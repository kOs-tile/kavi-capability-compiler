from __future__ import annotations
import fnmatch, hashlib, json, re, time

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def _tokens(value):
    return re.findall(r"[a-z0-9]+", str(value).lower())

def _phrase(text, phrase):
    pattern=r"(?<![a-z0-9])"+r"\\s+".join(re.escape(x) for x in phrase.split())+r"(?![a-z0-9])"
    return bool(re.search(pattern,text.lower()))

def analyze_capability(tool):
    annotations = dict(tool.get("annotations") or {})
    name = tool.get("name","")
    description = tool.get("description","")
    name_tokens = _tokens(name)
    desc_tokens = _tokens(description)
    leading = desc_tokens[0] if desc_tokens else ""
    evidence = []
    for key, value in annotations.items():
        if value is not None:
            evidence.append({"kind":"annotation","key":key,"value":value})

    delete_actions={"delete","remove","destroy","drop","clear","flush","pop","trim","teardown"}
    execute_actions={"exec","execute","evaluate","shell"}
    financial_actions={"payment","transfer","trade","purchase"}
    write_actions={"create","update","write","edit","merge","upload","add","append","set","put",
        "insert","rename","push","mark","ack","acknowledge","connect","disconnect","pause","resume",
        "upgrade","build","replace","touch","expire","move","patch","containerize","join","leave"}
    read_actions={"read","get","list","search","fetch","inspect","status","snapshot","show","find",
        "query","describe","count","scan","preview","discover","check","validate","explain","diff",
        "log","wait","simulate","info","retrieve"}
    external_actions={"send","publish"}

    # Name action evidence is preferred over incidental nouns in descriptions.
    # Destructive/high-impact actions take precedence.
    effect=None; confidence=0.0
    matches=[x for x in name_tokens if x in delete_actions]
    if matches or leading in delete_actions:
        effect,confidence="delete",0.95
        evidence.append({"kind":"lexical","source":"action","effect":"delete","matches":matches or [leading],"confidence":confidence})
    elif any(x in execute_actions for x in name_tokens) or leading in execute_actions or ({"rce","equivalent"} <= set(desc_tokens)) or _phrase(description,"arbitrary javascript"):
        matches=[x for x in name_tokens if x in execute_actions]
        effect,confidence="execute",0.95
        evidence.append({"kind":"lexical","source":"action","effect":"execute","matches":matches or [leading or "explicit execution evidence"],"confidence":confidence})
    elif any(x in financial_actions for x in name_tokens) or leading in financial_actions:
        matches=[x for x in name_tokens if x in financial_actions]
        effect,confidence="financial",0.95
        evidence.append({"kind":"lexical","source":"action","effect":"financial","matches":matches or [leading],"confidence":confidence})
    elif "deploy" in name_tokens or leading=="deploy" or _phrase(description,"publish production"):
        effect,confidence="deploy",0.95
        evidence.append({"kind":"lexical","source":"action","effect":"deploy","matches":["deploy"],"confidence":confidence})

    # Multi-operation and generic manage/run-query surfaces are context dependent
    # unless a later capsule constrains the operation.
    mixed_markers=("list, create, close","list/create/close","create, close, or select")
    explicit_mixed=any(m in description.lower() for m in mixed_markers)
    desc_has_read=any(x in read_actions for x in desc_tokens)
    desc_has_write=any(x in write_actions for x in desc_tokens)
    if effect is None and (explicit_mixed or (desc_has_read and desc_has_write) or "manage" in name_tokens or leading=="manage" or ("run" in name_tokens and "query" in name_tokens)):
        effect,confidence="mixed",0.85
        evidence.append({"kind":"lexical","source":"action","effect":"mixed","matches":["context-dependent operation"],"confidence":confidence})

    if effect is None:
        write_matches=[x for x in name_tokens if x in write_actions or x in {"lpush","rpush","hset","sadd","zadd","xadd"}]
        external_match=("message" in name_tokens and any(x in {"add","send","post"} for x in name_tokens)) or any(x in external_actions for x in name_tokens)
        if external_match:
            effect,confidence="external_message",0.85
            evidence.append({"kind":"lexical","source":"name_action","effect":effect,"matches":[x for x in name_tokens if x in external_actions or x in {"message","send","post"}],"confidence":confidence})
        elif write_matches:
            effect,confidence="write",0.85
            evidence.append({"kind":"lexical","source":"name_action","effect":effect,"matches":write_matches,"confidence":confidence})
        else:
            read_matches=[x for x in name_tokens if x in read_actions]
            if read_matches:
                effect,confidence="read",0.85
                evidence.append({"kind":"lexical","source":"name_action","effect":effect,"matches":read_matches,"confidence":confidence})

    # Only use the description's leading action when the tool name is inconclusive.
    if effect is None:
        if leading in write_actions:
            effect,confidence="write",0.75
        elif leading in read_actions:
            effect,confidence="read",0.75
        elif leading in external_actions:
            effect,confidence="external_message",0.75
        if effect is not None:
            evidence.append({"kind":"lexical","source":"description_leading_action","effect":effect,"matches":[leading],"confidence":confidence})

    # Declared metadata is evidence, not authority, and is consulted only after
    # explicit action evidence.
    if effect is None and annotations.get("destructiveHint") is True:
        effect, confidence = "write", 0.90
    if effect is None and annotations.get("readOnlyHint") is True:
        effect, confidence = "read", 0.90

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

def _validate_parameter_constraints(capability, constraints):
    params=constraints.get("parameters") or {}
    schema=capability.get("input_schema") or {}
    properties=schema.get("properties")
    if isinstance(properties,dict) and properties:
        unknown=sorted(set(params)-set(properties))
        if unknown:
            raise ValueError(f"Constraint references unknown parameter(s) for {capability['id']}: {unknown}")

def compile_capsule(inv,intent,policy,now=None):
    now=int(now or time.time()); by_id={c["id"]:c for c in inv["capabilities"]}
    grants=[]; approvals=[]; denials=[]
    for cid in intent.get("capabilities",[]):
        if cid not in by_id: raise ValueError(f"Capability absent from inventory: {cid}")
        c=by_id[cid]; d=decide(policy,c)
        constraints=_constraint_for(intent,cid)
        _validate_parameter_constraints(c,constraints)
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
        if isinstance(rule,dict) and rule.get("required") is True and key not in params:
            return {"allowed":False,"reason":f"required_parameter_missing:{key}"}
        if key not in params: continue
        value=params[key]
        if isinstance(rule,dict):
            if "type" in rule:
                kinds={"string":str,"integer":int,"number":(int,float),"boolean":bool,"array":list,"object":dict}
                expected=kinds.get(rule["type"])
                if expected is None: return {"allowed":False,"reason":f"unsupported_parameter_type_rule:{key}"}
                if not isinstance(value,expected) or (rule["type"] in {"integer","number"} and isinstance(value,bool)):
                    return {"allowed":False,"reason":f"parameter_type_mismatch:{key}"}
            if "max" in rule and value > rule["max"]: return {"allowed":False,"reason":f"parameter_above_max:{key}"}
            if "min" in rule and value < rule["min"]: return {"allowed":False,"reason":f"parameter_below_min:{key}"}
            if "enum" in rule and value not in rule["enum"]: return {"allowed":False,"reason":f"parameter_not_allowed:{key}"}
            if "max_length" in rule and len(value) > rule["max_length"]: return {"allowed":False,"reason":f"parameter_too_long:{key}"}
            if "pattern" in rule and not re.fullmatch(rule["pattern"],str(value)): return {"allowed":False,"reason":f"parameter_pattern_mismatch:{key}"}
        elif value != rule:
            return {"allowed":False,"reason":f"parameter_mismatch:{key}"}
    return {"allowed":True,"reason":"granted"}
