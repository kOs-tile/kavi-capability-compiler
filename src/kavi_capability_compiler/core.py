from __future__ import annotations
import fnmatch, hashlib, json, re, time

INVENTORY_VERSION="kcc.inventory.v1"
INVENTORY_LOCK_VERSION="kcc.inventory-lock.v1"
CAPSULE_VERSION="kcc.capsule.v1"

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
    def norm(x):
        text=str(x).strip().lower().replace(" ", "-")
        return text.replace("%","%25").replace(":","%3a")
    return f"{norm(provider)}:{norm(server)}:{norm(name)}"

def scan_mcp_snapshot(snapshot):
    tools = snapshot.get("tools") or snapshot.get("result",{}).get("tools") or []
    server = snapshot.get("server",{}).get("name","mcp")
    caps=[]; seen_ids=set()
    for t in tools:
        schema=t.get("inputSchema") or {}
        effect, confidence=classify(t)
        fp=digest({"name":t.get("name"),"description":t.get("description"),"schema":schema,
            "annotations":t.get("annotations") or {}})
        cid=capability_id("mcp",server,t["name"])
        if cid in seen_ids:
            raise ValueError(f"Duplicate canonical capability identity: {cid}")
        seen_ids.add(cid)
        caps.append({"id":cid,"provider":"mcp","server":server,
            "name":t["name"],"description":t.get("description",""),"input_schema":schema,
            "fingerprint":fp,"effect":effect,"confidence":confidence,
            "analysis":analyze_capability(t),
            "annotations":t.get("annotations") or {}})
    inv={"version":INVENTORY_VERSION,"capabilities":caps}
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
    if inv.get("version") != INVENTORY_VERSION:
        raise ValueError(f"Unsupported inventory contract: {inv.get('version')}")
    requested=intent.get("capabilities",[])
    if not isinstance(requested,list) or not all(isinstance(x,str) and x for x in requested):
        raise ValueError("Intent capabilities must be a list of non-empty capability IDs")
    if not _inventory_integrity(inv,semantic_ids=requested):
        raise ValueError("Invalid inventory integrity")
    task=intent.get("task")
    if task is not None and not isinstance(task,str):
        raise ValueError("Task must be a string or null")
    global_constraints=intent.get("constraints",{})
    if not isinstance(global_constraints,dict):
        raise ValueError("Intent constraints must be an object")
    now=int(now if now is not None else time.time()); by_id={c["id"]:c for c in inv["capabilities"]}
    grants=[]; approvals=[]; denials=[]
    for cid in requested:
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
    cap={"version":CAPSULE_VERSION,"status":status,"issued_at":now,"expires_at":now+ttl,
        "inventory_digest":inv["digest"],"intent_digest":digest(intent),"policy_digest":digest(policy),
        "task":task,"constraints":global_constraints,
        "grants":grants,"approvals":approvals,"denials":denials,"fail_closed":True}
    cap["capsule_id"]=digest(cap)
    return cap

def verify_capsule(cap,inv,now=None):
    if not isinstance(cap,dict) or not isinstance(inv,dict):
        return {"valid":False,"checks":[{"name":"shape","ok":False}]}
    body=dict(cap); claimed=body.pop("capsule_id",None)
    try:
        integrity=isinstance(claimed,str) and claimed==digest(body)
    except (TypeError,ValueError):
        integrity=False
    checks=[
        ("integrity",integrity),
        ("version",cap.get("version")==CAPSULE_VERSION),
        ("fail_closed",cap.get("fail_closed") is True),
        ("inventory_version",inv.get("version")==INVENTORY_VERSION),
        ("inventory",cap.get("inventory_digest")==inv.get("digest")),
    ]
    rows=inv.get("capabilities",[])
    inventory_shape=isinstance(rows,list) and all(isinstance(x,dict) and isinstance(x.get("id"),str) and isinstance(x.get("fingerprint"),str) for x in rows)
    by_id={c["id"]:c for c in rows} if inventory_shape else {}
    shape=True; bound=True
    for key in ("grants","approvals","denials"):
        entries=cap.get(key,[])
        if not isinstance(entries,list):
            shape=False; bound=False; continue
        for entry in entries:
            if not isinstance(entry,dict) or not isinstance(entry.get("id"),str) or not isinstance(entry.get("fingerprint"),str):
                shape=False; bound=False; continue
            if by_id.get(entry["id"],{}).get("fingerprint") != entry["fingerprint"]:
                bound=False
    try:
        current=int(now if now is not None else time.time())
        expiry=int(cap.get("expires_at",0))
        expiry_ok=current < expiry
    except (TypeError,ValueError):
        expiry_ok=False
    checks += [("shape",shape and inventory_shape),("fingerprints",bound),("expiry",expiry_ok)]
    return {"valid":all(v for _,v in checks),"checks":[{"name":n,"ok":v} for n,v in checks]}


def inventory_lock(inv):
    if inv.get("version") != INVENTORY_VERSION:
        raise ValueError(f"Unsupported inventory contract: {inv.get('version')}")
    if not _inventory_integrity(inv,semantic_ids=()):
        raise ValueError("Invalid inventory integrity")
    entries=[{"id":c["id"],"fingerprint":c["fingerprint"]} for c in inv["capabilities"]]
    lock={"version":INVENTORY_LOCK_VERSION,"inventory_digest":inv["digest"],"capabilities":sorted(entries,key=lambda x:x["id"])}
    lock["digest"]=digest(lock)
    return lock

def diff_inventory_lock(lock, inv):
    if lock.get("version") != INVENTORY_LOCK_VERSION:
        raise ValueError(f"Unsupported inventory lock contract: {lock.get('version')}")
    if inv.get("version") != INVENTORY_VERSION:
        raise ValueError(f"Unsupported inventory contract: {inv.get('version')}")
    if not _inventory_lock_integrity(lock):
        raise ValueError("Invalid inventory lock integrity")
    if not _inventory_integrity(inv,semantic_ids=()):
        raise ValueError("Invalid inventory integrity")
    old={x["id"]:x["fingerprint"] for x in lock.get("capabilities",[])}
    new={x["id"]:x["fingerprint"] for x in inv.get("capabilities",[])}
    added=sorted(set(new)-set(old)); removed=sorted(set(old)-set(new))
    changed=sorted(k for k in set(old)&set(new) if old[k]!=new[k])
    return {"clean":not (added or removed or changed),"added":added,"removed":removed,"changed":changed}


def _inventory_lock_integrity(lock):
    if not isinstance(lock,dict) or lock.get("version") != INVENTORY_LOCK_VERSION:
        return False
    claimed=lock.get("digest")
    rows=lock.get("capabilities")
    if not isinstance(claimed,str) or not isinstance(rows,list):
        return False
    seen=set()
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get("id"),str) or not isinstance(row.get("fingerprint"),str):
            return False
        if row["id"] in seen:
            return False
        seen.add(row["id"])
    try:
        body=dict(lock)
        body.pop("digest",None)
        return claimed==digest(body)
    except (TypeError,ValueError):
        return False


def _inventory_integrity(inv, semantic_ids=None):
    """Validate inventory envelope and the semantic rows relevant to this operation.

    Every call validates version, digest, canonical identities, and duplicate IDs
    across the complete inventory. Expensive fingerprint/effect re-analysis can
    be bounded to the capability IDs that may receive or exercise authority.
    Passing None performs a full semantic re-analysis.
    """
    if not isinstance(inv,dict) or inv.get("version") != INVENTORY_VERSION:
        return False
    claimed=inv.get("digest")
    caps=inv.get("capabilities")
    if not isinstance(claimed,str) or not isinstance(caps,list):
        return False

    adapter=inv.get("adapter")
    if adapter not in {None,"universal-manifest.v1"}:
        return False

    selected=None if semantic_ids is None else set(semantic_ids)
    entries=[]; seen_ids=set()
    try:
        for c in caps:
            if not isinstance(c,dict):
                return False
            server=c.get("server")
            name=c.get("name")
            fingerprint=c.get("fingerprint")
            if not isinstance(server,str) or not isinstance(name,str) or not isinstance(fingerprint,str):
                return False

            expected_id=capability_id("kcc" if adapter else "mcp",server,name)
            if c.get("id") != expected_id or expected_id in seen_ids:
                return False
            seen_ids.add(expected_id)
            entries.append({"id":expected_id,"fingerprint":fingerprint})

            if selected is not None and expected_id not in selected:
                continue

            description=c.get("description","")
            schema=c.get("input_schema") or {}
            annotations=c.get("annotations") or {}
            if adapter:
                expected_fp=digest({
                    "namespace":server,
                    "name":name,
                    "description":str(description or ""),
                    "input_schema":schema,
                    "annotations":annotations,
                })
            else:
                expected_fp=digest({
                    "name":name,
                    "description":description,
                    "schema":schema,
                    "annotations":annotations,
                })
            if fingerprint != expected_fp:
                return False

            analysis=analyze_capability({
                "name":name,
                "description":description,
                "inputSchema":schema,
                "annotations":annotations,
            })
            expected_effect="unknown" if analysis["effect"]=="mixed" else analysis["effect"]
            if c.get("effect") != expected_effect:
                return False
            if c.get("confidence") != analysis["confidence"]:
                return False
            if c.get("analysis") != analysis:
                return False

        if selected is not None and not selected.issubset(seen_ids):
            return False

        if adapter:
            expected=digest({
                "version":inv["version"],
                "adapter":adapter,
                "capabilities":sorted(entries,key=lambda x:x["id"]),
            })
        else:
            body=dict(inv)
            body.pop("digest",None)
            expected=digest(body)
    except (KeyError,TypeError,ValueError):
        return False
    return claimed==expected


def _verification_failure_reason(verification, *, inventory_bound=False):
    failed={x["name"] for x in verification.get("checks",[]) if not x.get("ok")}
    if "integrity" in failed:
        return "invalid_capsule_integrity"
    if "version" in failed:
        return "unsupported_capsule_version"
    if "fail_closed" in failed:
        return "fail_closed_required"
    if inventory_bound and failed.intersection({"inventory","fingerprints","shape"}):
        return "inventory_drift"
    if "expiry" in failed:
        return "expired"
    return "invalid_capsule"


def authorize_call(cap, capability_id, operation=None, parameters=None, now=None, inventory=None):
    if not isinstance(cap,dict):
        return {"allowed":False,"reason":"invalid_capsule_shape"}

    inventory_bound=inventory is not None
    if inventory_bound:
        if not isinstance(inventory,dict):
            return {"allowed":False,"reason":"invalid_inventory_binding"}
        if inventory.get("version") != INVENTORY_VERSION:
            return {"allowed":False,"reason":"unsupported_inventory_version"}
        if not _inventory_integrity(inventory,semantic_ids=(capability_id,)):
            return {"allowed":False,"reason":"invalid_inventory_integrity"}
        verification_inventory=inventory
    else:
        verification_inventory={
            "version":INVENTORY_VERSION,
            "digest":cap.get("inventory_digest"),
            "capabilities":[],
        }
        for key in ("grants","approvals","denials"):
            entries=cap.get(key,[])
            if not isinstance(entries,list):
                return {"allowed":False,"reason":"invalid_capsule_shape"}
            for entry in entries:
                if not isinstance(entry,dict) or not isinstance(entry.get("id"),str) or not isinstance(entry.get("fingerprint"),str):
                    return {"allowed":False,"reason":"invalid_capsule_shape"}
                verification_inventory["capabilities"].append({"id":entry["id"],"fingerprint":entry["fingerprint"]})

    verification=verify_capsule(cap,verification_inventory,now=now)
    if not verification["valid"]:
        return {
            "allowed":False,
            "reason":_verification_failure_reason(verification,inventory_bound=inventory_bound),
            "verification":verification,
        }
    grants={x["id"]:x for x in cap.get("grants",[])}
    approvals={x["id"]:x for x in cap.get("approvals",[])}
    denials={x["id"]:x for x in cap.get("denials",[])}
    if capability_id in approvals:
        return {
            "allowed":False,
            "reason":"approval_required",
            "capability":approvals[capability_id],
        }
    if capability_id in denials:
        return {
            "allowed":False,
            "reason":"capability_denied",
            "capability":denials[capability_id],
        }
    if capability_id not in grants:
        return {"allowed":False,"reason":"capability_not_granted"}
    entry=grants[capability_id]; constraints=entry.get("constraints") or {}
    ops=constraints.get("operations")
    if ops and operation not in ops:
        return {"allowed":False,"reason":"operation_not_granted"}
    try:
        params=dict(parameters or {})
    except (TypeError,ValueError):
        return {"allowed":False,"reason":"invalid_parameters"}
    parameter_rules=constraints.get("parameters") if "parameters" in constraints else None
    if parameter_rules is not None:
        if not isinstance(parameter_rules,dict):
            return {"allowed":False,"reason":"invalid_parameter_constraints"}
        unexpected=sorted(set(params)-set(parameter_rules))
        if unexpected:
            return {
                "allowed":False,
                "reason":f"parameter_not_granted:{unexpected[0]}",
                "parameters":unexpected,
            }
    for key, rule in (parameter_rules or {}).items():
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
