from __future__ import annotations
import fnmatch, hashlib, json, time

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def classify(tool):
    # MCP annotations are declared evidence, not proof. Prefer explicit
    # read-only/destructive declarations over lexical heuristics, while
    # preserving unknown when the declaration is incomplete.
    annotations = tool.get("annotations") or {}
    if annotations.get("readOnlyHint") is True:
        return "read", 0.95
    if annotations.get("destructiveHint") is True:
        return "delete", 0.90

    text = " ".join([tool.get("name",""), tool.get("description","")]).lower()
    rules = [
        ("delete", ("delete","remove","destroy","drop")),
        ("deploy", ("deploy","release","publish production")),
        ("execute", ("exec","shell","command","run process")),
        ("financial", ("payment","transfer","trade","purchase")),
        ("external_message", ("send email","send message","post message")),
        ("write", ("create","update","write","edit","merge")),
        ("read", ("read","get","list","search","fetch","inspect")),
    ]
    for effect, words in rules:
        if any(w in text for w in words):
            return effect, 0.8
    return "unknown", 0.0

def scan_mcp_snapshot(snapshot):
    tools = snapshot.get("tools") or snapshot.get("result",{}).get("tools") or []
    server = snapshot.get("server",{}).get("name","mcp")
    caps=[]
    for t in tools:
        schema=t.get("inputSchema") or {}
        effect, confidence=classify(t)
        fp=digest({"name":t.get("name"),"description":t.get("description"),"schema":schema,
            "annotations":t.get("annotations") or {}})
        caps.append({"id":f"mcp:{server}:{t['name']}","provider":"mcp","server":server,
            "name":t["name"],"description":t.get("description",""),"input_schema":schema,
            "fingerprint":fp,"effect":effect,"confidence":confidence,
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

def compile_capsule(inv,intent,policy,now=None):
    now=int(now or time.time()); by_id={c["id"]:c for c in inv["capabilities"]}
    grants=[]; approvals=[]; denials=[]
    for cid in intent.get("capabilities",[]):
        if cid not in by_id: raise ValueError(f"Capability absent from inventory: {cid}")
        c=by_id[cid]; d=decide(policy,c)
        if c["effect"]=="unknown" and d=="allow": d="approval"
        entry={"id":cid,"fingerprint":c["fingerprint"],"effect":c["effect"]}
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
