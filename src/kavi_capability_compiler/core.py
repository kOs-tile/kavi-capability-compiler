from __future__ import annotations
import fnmatch, hashlib, json, time

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def analyze_capability(tool):
    annotations = dict(tool.get("annotations") or {})
    text = " ".join([tool.get("name",""), tool.get("description","")]).lower()
    evidence = []
    for key, value in annotations.items():
        if value is not None:
            evidence.append({"kind":"annotation","key":key,"value":value})

    dangerous_rules = [
        ("delete", ("delete","remove","destroy","drop")),
        ("deploy", ("deploy","publish production")),
        ("execute", ("rce-equivalent","arbitrary javascript","evaluate javascript","exec","shell","command","run process")),
        ("financial", ("payment","transfer","trade","purchase")),
    ]
    effect = None
    confidence = 0.0
    for candidate, words in dangerous_rules:
        matched = [w for w in words if w in text]
        if matched:
            effect, confidence = candidate, 0.95
            evidence.append({"kind":"lexical","effect":candidate,"matches":matched,"confidence":confidence})
            break

    mixed_markers = ("list, create, close", "list/create/close", "create, close, or select")
    if effect is None and any(m in text for m in mixed_markers):
        effect, confidence = "mixed", 0.85
        evidence.append({"kind":"lexical","effect":"mixed","matches":["multi-operation description"],"confidence":confidence})

    if effect is None and annotations.get("destructiveHint") is True:
        effect, confidence = "write", 0.90
    if effect is None and annotations.get("readOnlyHint") is True:
        effect, confidence = "read", 0.90

    if effect is None:
        rules = [
            ("external_message", ("send email","send message","post message")),
            ("write", ("create","update","write","edit","merge","upload","add observation","commit","checkout","switches branches")),
            ("read", ("read","get","list","search","fetch","inspect","status","snapshot","show","convert time")),
        ]
        for candidate, words in rules:
            matched = [w for w in words if w in text]
            if matched:
                effect, confidence = candidate, 0.8
                evidence.append({"kind":"lexical","effect":candidate,"matches":matched,"confidence":confidence})
                break

    if effect is None:
        effect = "unknown"

    risk_flags = []
    if annotations.get("destructiveHint") is True or effect == "delete":
        risk_flags.append("destructive")
    if annotations.get("openWorldHint") is True:
        risk_flags.append("open_world")
    if annotations.get("idempotentHint") is False:
        risk_flags.append("non_idempotent")
    if effect in {"unknown","mixed"}:
        risk_flags.append("context_dependent")
    if annotations.get("readOnlyHint") is True and effect not in {"read","unknown"}:
        risk_flags.append("annotation_conflict")

    return {"effect":effect,"confidence":confidence,"risk_flags":risk_flags,
        "declared":annotations,"evidence":evidence}

def classify(tool):
    analysis = analyze_capability(tool)
    effect = analysis["effect"]
    # Preserve v0 classifier contract while v2 can represent mixed authority.
    if effect == "mixed":
        return "unknown", analysis["confidence"]
    return effect, analysis["confidence"]

def capability_id(provider, server, name):
    def norm(x): return str(x).strip().lower().replace(" ", "-")
    return f"{norm(provider)}:{norm(server)}:{norm(name)}"

def scan_mcp_snapshot(snapshot):
    tools = snapshot.get("tools") or snapshot.get("result",{}).get("tools") or []
    server = snapshot.get("server",{}).get("name","mcp")
    caps=[]
    for t in tools:
        schema=t.get("inputSchema") or {}
        effect, confidence=classify(t)
        fp=digest({"name":t.get("name"),"description":t.get("description"),"schema":schema,
            "annotations":t.get("annotations") or {}})
        caps.append({"id":capability_id("mcp",server,t["name"]),"provider":"mcp","server":server,
            "name":t["name"],"description":t.get("description",""),"input_schema":schema,
            "fingerprint":fp,"effect":effect,"confidence":confidence,
            "analysis":analyze_capability(t),
            "annotations":t.get("annotations") or {}})
    inv={"version":"kcc.inventory.v0","capabilities":caps}
    inv["digest"]=digest(inv)
    return inv

def audit_inventory(inv):
    findings=[]
    for c in inv["capabilities"]:
        if c["effect"]=="unknown" or c["confidence"]<0.5:
            findings.append({"code":"KCC-A100","severity":"high","capability":c["id"],"message":"Unknown or low-confidence side effect"})
        if c["effect"] in {"delete","execute","financial","deploy"}:
            findings.append({"code":"KCC-A110","severity":"high","capability":c["id"],"message":"High-impact side effect"})
        elif c["effect"] in {"write","external_message"}:
            findings.append({"code":"KCC-A111","severity":"medium","capability":c["id"],"message":"External mutation"})
        if not c["input_schema"]:
            findings.append({"code":"KCC-A130","severity":"medium","capability":c["id"],"message":"Missing or unbounded input schema"})
    out={"version":"kcc.audit.v0","inventory_digest":inv["digest"],"findings":findings}
    out["digest"]=digest(out)
    return out

def _matches(rule,c):
    ids=rule.get("capabilities",["*"])
    return any(fnmatch.fnmatch(c["id"],p) for p in ids) and (not rule.get("effects") or c["effect"] in rule["effects"]) and (not rule.get("servers") or c["server"] in rule["servers"])

def decide(policy,c):
    for decision in ("deny","approval","allow"):
        if any(_matches(r,c) for r in policy.get(decision,[])):
            return decision
    return policy.get("default","deny")

def _constraint_for(intent, cid):
    raw=(intent.get("capability_constraints") or {}).get(cid,{})
    if not isinstance(raw,dict): raise ValueError(f"Invalid capability constraint: {cid}")
    allowed=set(raw).intersection({"operations","parameters"})
    if set(raw)-allowed: raise ValueError(f"Unsupported capability constraint: {cid}")
    out={}
    if "operations" in raw:
        ops=raw["operations"]
        if not isinstance(ops,list) or not ops or not all(isinstance(x,str) and x for x in ops):
            raise ValueError(f"Invalid operations constraint: {cid}")
        out["operations"]=sorted(set(ops))
    if "parameters" in raw:
        params=raw["parameters"]
        if not isinstance(params,dict): raise ValueError(f"Invalid parameters constraint: {cid}")
        out["parameters"]=params
    return out

def compile_capsule(inv,intent,policy,now=None):
    now=int(now or time.time()); by_id={c["id"]:c for c in inv["capabilities"]}
    grants=[]; approvals=[]; denials=[]
    for cid in intent.get("capabilities",[]):
        if cid not in by_id: raise ValueError(f"Capability absent from inventory: {cid}")
        c=by_id[cid]; d=decide(policy,c)
        constraints=_constraint_for(intent,cid)
        analysis=c.get("analysis") or {"effect":c["effect"],"risk_flags":[]}
        mixed=analysis.get("effect")=="mixed"
        if c["effect"]=="unknown" and d=="allow" and not (mixed and constraints.get("operations")):
            d="approval"
        if mixed and not constraints.get("operations"):
            d="approval" if d!="deny" else d
        entry={"id":cid,"fingerprint":c["fingerprint"],"effect":c["effect"],
            "risk_flags":analysis.get("risk_flags",[]),"constraints":constraints}
        {"allow":grants,"approval":approvals,"deny":denials}[d].append(entry)
    ttl=max(1,min(int(intent.get("ttl_seconds",900)),86400))
    status="denied" if denials else ("approval_required" if approvals else "ready")
    cap={"version":"kcc.capsule.v0","status":status,"issued_at":now,"expires_at":now+ttl,
        "inventory_digest":inv["digest"],"intent_digest":digest(intent),"policy_digest":digest(policy),
        "task":intent.get("task"),"constraints":intent.get("constraints",{}),
        "grants":grants,"approvals":approvals,"denials":denials,"fail_closed":True}
    cap["capsule_id"]=digest(cap)
    return cap

def verify_capsule(cap,inv,now=None):
    body=dict(cap); claimed=body.pop("capsule_id",None)
    checks=[("integrity",claimed==digest(body)),("inventory",cap.get("inventory_digest")==inv.get("digest"))]
    by_id={c["id"]:c for c in inv["capabilities"]}
    bound=all(by_id.get(x["id"],{}).get("fingerprint")==x["fingerprint"] for k in ("grants","approvals","denials") for x in cap.get(k,[]))
    checks += [("fingerprints",bound),("expiry",int(now or time.time()) < cap.get("expires_at",0))]
    return {"valid":all(v for _,v in checks),"checks":[{"name":n,"ok":v} for n,v in checks]}


def inventory_lock(inv):
    entries=[{"id":c["id"],"fingerprint":c["fingerprint"]} for c in inv["capabilities"]]
    lock={"version":"kcc.inventory-lock.v0","inventory_digest":inv["digest"],"capabilities":sorted(entries,key=lambda x:x["id"])}
    lock["digest"]=digest(lock)
    return lock

def diff_inventory_lock(lock, inv):
    old={x["id"]:x["fingerprint"] for x in lock.get("capabilities",[])}
    new={x["id"]:x["fingerprint"] for x in inv.get("capabilities",[])}
    added=sorted(set(new)-set(old)); removed=sorted(set(old)-set(new))
    changed=sorted(k for k in set(old)&set(new) if old[k]!=new[k])
    return {"clean":not (added or removed or changed),"added":added,"removed":removed,"changed":changed}


def authorize_call(cap, capability_id, operation=None, parameters=None, now=None):
    if not verify_capsule(cap, {"digest":cap.get("inventory_digest"), "capabilities":[
        {"id":x["id"],"fingerprint":x["fingerprint"]}
        for k in ("grants","approvals","denials") for x in cap.get(k,[])
    ]}, now=now)["checks"][0]["ok"]:
        return {"allowed":False,"reason":"invalid_capsule_integrity"}
    if int(now or time.time()) >= cap.get("expires_at",0):
        return {"allowed":False,"reason":"expired"}
    grants={x["id"]:x for x in cap.get("grants",[])}
    if capability_id not in grants:
        return {"allowed":False,"reason":"capability_not_granted"}
    entry=grants[capability_id]; constraints=entry.get("constraints") or {}
    ops=constraints.get("operations")
    if ops and operation not in ops:
        return {"allowed":False,"reason":"operation_not_granted"}
    params=parameters or {}
    for key, rule in (constraints.get("parameters") or {}).items():
        if key not in params: continue
        value=params[key]
        if isinstance(rule,dict):
            if "max" in rule and value > rule["max"]: return {"allowed":False,"reason":f"parameter_above_max:{key}"}
            if "min" in rule and value < rule["min"]: return {"allowed":False,"reason":f"parameter_below_min:{key}"}
            if "enum" in rule and value not in rule["enum"]: return {"allowed":False,"reason":f"parameter_not_allowed:{key}"}
        elif value != rule:
            return {"allowed":False,"reason":f"parameter_mismatch:{key}"}
    return {"allowed":True,"reason":"granted"}
