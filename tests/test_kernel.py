import copy
from kavi_capability_compiler.core import *

SNAP={"server":{"name":"demo"},"tools":[
 {"name":"search_code","description":"Search code","inputSchema":{"type":"object"}},
 {"name":"create_issue","description":"Create issue","inputSchema":{"type":"object"}},
 {"name":"delete_repository","description":"Delete repository","inputSchema":{"type":"object"}},
 {"name":"mystery_action","description":"Do something","inputSchema":{"type":"object"}}]}

def test_scan_and_audit():
    inv=scan_mcp_snapshot(SNAP); assert len(inv["capabilities"])==4
    assert {c["effect"] for c in inv["capabilities"]} >= {"read","write","delete","unknown"}
    findings=audit_inventory(inv)["findings"]
    assert any(f["code"]=="KCC-A110" for f in findings)
    assert any(f["code"]=="KCC-A100" for f in findings)

def test_compile_least_authority():
    inv=scan_mcp_snapshot(SNAP)
    cap=compile_capsule(inv,{"task":"review","capabilities":["mcp:demo:search_code","mcp:demo:create_issue"]},
        {"default":"deny","allow":[{"effects":["read"]}],"approval":[{"effects":["write"]}]},now=100)
    assert cap["status"]=="approval_required" and len(cap["grants"])==1 and len(cap["approvals"])==1

def test_deny_precedence():
    inv=scan_mcp_snapshot(SNAP)
    cap=compile_capsule(inv,{"capabilities":["mcp:demo:delete_repository"]},
        {"default":"allow","allow":[{"capabilities":["*"]}],"deny":[{"effects":["delete"]}]},now=100)
    assert cap["status"]=="denied"

def test_unknown_never_auto_allows():
    inv=scan_mcp_snapshot(SNAP)
    assert compile_capsule(inv,{"capabilities":["mcp:demo:mystery_action"]},{"default":"allow"},now=100)["status"]=="approval_required"

def test_missing_capability_fails_closed():
    inv=scan_mcp_snapshot(SNAP)
    try: compile_capsule(inv,{"capabilities":["mcp:demo:nope"]},{"default":"allow"},now=100)
    except ValueError: pass
    else: assert False

def test_verify_detects_drift():
    inv=scan_mcp_snapshot(SNAP); cap=compile_capsule(inv,{"capabilities":["mcp:demo:search_code"]},{"default":"allow"},now=100)
    assert verify_capsule(cap,inv,now=101)["valid"]
    drift=copy.deepcopy(inv); drift["capabilities"][0]["fingerprint"]="changed"
    assert not verify_capsule(cap,drift,now=101)["valid"]

def test_verify_detects_expiry():
    inv=scan_mcp_snapshot(SNAP); cap=compile_capsule(inv,{"capabilities":["mcp:demo:search_code"],"ttl_seconds":1},{"default":"allow"},now=100)
    assert not verify_capsule(cap,inv,now=102)["valid"]


def test_declared_read_only_cannot_override_destructive_evidence():
    tool={"name":"delete_repository","description":"Delete repository permanently","inputSchema":{"type":"object"},"annotations":{"readOnlyHint":True}}
    effect, confidence=classify(tool)
    assert effect != "read"
    assert confidence >= 0.5

def test_declared_non_destructive_cannot_override_execute_evidence():
    tool={"name":"run_shell_command","description":"Execute a shell command","inputSchema":{"type":"object"},"annotations":{"destructiveHint":False}}
    effect, confidence=classify(tool)
    assert effect == "execute"
    assert confidence >= 0.5


def test_capability_analysis_separates_effect_from_risk():
    a=analyze_capability({"name":"write_file","description":"Create new file or overwrite existing","annotations":{"destructiveHint":True}})
    assert a["effect"] == "write"
    assert "destructive" in a["risk_flags"]
    assert a["declared"]["destructiveHint"] is True


def test_mixed_operation_capability_is_not_silently_safe():
    a=analyze_capability({"name":"browser_tabs","description":"List, create, close, or select a browser tab."})
    assert a["effect"] == "mixed"
    assert "context_dependent" in a["risk_flags"]


def test_analysis_preserves_evidence_provenance():
    a=analyze_capability({"name":"delete_repository","description":"Delete repository permanently","annotations":{"readOnlyHint":True}})
    assert a["effect"] == "delete"
    assert any(e["kind"] == "lexical" for e in a["evidence"])
    assert any(e["kind"] == "annotation" for e in a["evidence"])


def test_capsule_binds_operation_and_parameter_constraints():
    snap={"server":{"name":"browser"},"tools":[{"name":"browser_tabs","description":"List, create, close, or select a browser tab.","inputSchema":{"type":"object"}}]}
    inv=scan_mcp_snapshot(snap); cid="mcp:browser:browser_tabs"
    intent={"capabilities":[cid],"capability_constraints":{cid:{"operations":["list"],"parameters":{"tab_index":{"max":3}}}}}
    cap=compile_capsule(inv,intent,{"default":"allow"},now=100)
    assert cap["grants"][0]["constraints"]["operations"] == ["list"]
    assert cap["grants"][0]["constraints"]["parameters"]["tab_index"]["max"] == 3


def test_mixed_capability_without_operation_constraint_requires_approval():
    snap={"server":{"name":"browser"},"tools":[{"name":"browser_tabs","description":"List, create, close, or select a browser tab.","inputSchema":{"type":"object"}}]}
    inv=scan_mcp_snapshot(snap); cid="mcp:browser:browser_tabs"
    cap=compile_capsule(inv,{"capabilities":[cid]},{"default":"allow"},now=100)
    assert cap["status"] == "approval_required"


def test_inventory_lock_detects_added_removed_and_changed():
    inv=scan_mcp_snapshot(SNAP); lock=inventory_lock(inv)
    assert diff_inventory_lock(lock,inv)["clean"]
    changed=copy.deepcopy(SNAP); changed["tools"][0]["description"]="Search code with expanded scope"
    drift=scan_mcp_snapshot(changed); d=diff_inventory_lock(lock,drift)
    assert not d["clean"] and "mcp:demo:search_code" in d["changed"]
    added=copy.deepcopy(SNAP); added["tools"].append({"name":"new_tool","description":"Read new data","inputSchema":{"type":"object"}})
    assert "mcp:demo:new_tool" in diff_inventory_lock(lock,scan_mcp_snapshot(added))["added"]


def test_canonical_capability_identity_is_provider_scoped():
    assert capability_id("MCP","GitHub/GitHub-MCP-Server","Get_File_Contents") == "mcp:github/github-mcp-server:get_file_contents"


def test_authorize_call_enforces_operation_and_parameter_bounds():
    snap={"server":{"name":"browser"},"tools":[{"name":"browser_tabs","description":"List, create, close, or select a browser tab.","inputSchema":{"type":"object"}}]}
    inv=scan_mcp_snapshot(snap); cid="mcp:browser:browser_tabs"
    intent={"capabilities":[cid],"ttl_seconds":100,"capability_constraints":{cid:{"operations":["list"],"parameters":{"tab_index":{"min":0,"max":3}}}}}
    cap=compile_capsule(inv,intent,{"default":"allow"},now=100)
    assert authorize_call(cap,cid,"list",{"tab_index":2},now=101)["allowed"]
    assert authorize_call(cap,cid,"close",{"tab_index":2},now=101)["reason"] == "operation_not_granted"
    assert authorize_call(cap,cid,"list",{"tab_index":9},now=101)["reason"] == "parameter_above_max:tab_index"
    assert authorize_call(cap,"mcp:browser:other","list",{},now=101)["reason"] == "capability_not_granted"
    assert authorize_call(cap,cid,"list",{},now=201)["reason"] == "expired"


def test_action_matching_avoids_read_noun_collisions():
    cases=[
        {"name":"lpush","description":"Push a value onto the left of a Redis list"},
        {"name":"rpush","description":"Push a value onto the right of a Redis list"},
        {"name":"conversations_mark","description":"Mark a channel or DM as read"},
    ]
    for tool in cases:
        effect,_=classify(tool)
        assert effect != "read", (tool,effect)


def test_multi_action_tool_does_not_collapse_to_read():
    effect,_=classify({"name":"usergroups_me","description":"Manage your user group membership: list groups you're in, join a group, or leave a group."})
    assert effect != "read"


def test_browser_type_is_not_read_authority():
    effect,_=classify({"name":"browser_type","description":"Type text into editable element"})
    assert effect != "read"


def test_required_parameter_constraint_fails_closed():
    snap={"server":{"name":"svc"},"tools":[{"name":"update_item","description":"Update item","inputSchema":{"type":"object","properties":{"id":{"type":"string"}}}}]}
    inv=scan_mcp_snapshot(snap); cid="mcp:svc:update_item"
    intent={"capabilities":[cid],"ttl_seconds":100,"capability_constraints":{cid:{"parameters":{"id":{"required":True,"type":"string","pattern":"[A-Z]+-[0-9]+"}}}}}
    cap=compile_capsule(inv,intent,{"default":"allow"},now=100)
    assert authorize_call(cap,cid,parameters={},now=101)["reason"]=="required_parameter_missing:id"
    assert authorize_call(cap,cid,parameters={"id":"bad"},now=101)["reason"]=="parameter_pattern_mismatch:id"
    assert authorize_call(cap,cid,parameters={"id":"ABC-12"},now=101)["allowed"]


def test_constraint_unknown_schema_parameter_rejected_at_compile():
    snap={"server":{"name":"svc"},"tools":[{"name":"update_item","description":"Update item","inputSchema":{"type":"object","properties":{"id":{"type":"string"}}}}]}
    inv=scan_mcp_snapshot(snap); cid="mcp:svc:update_item"
    intent={"capabilities":[cid],"capability_constraints":{cid:{"parameters":{"ghost":{"required":True}}}}}
    try:
        compile_capsule(inv,intent,{"default":"allow"},now=100)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "unknown parameter" in str(e)

def test_capability_identity_escapes_reserved_segment_delimiters():
    left=capability_id("kcc","a:b","c")
    right=capability_id("kcc","a","b:c")
    assert left != right
    assert "%3a" in left and "%3a" in right


def test_mcp_scan_rejects_duplicate_canonical_identity():
    snap={"server":{"name":"demo"},"tools":[
        {"name":"Read Item","description":"Read item","inputSchema":{"type":"object"}},
        {"name":"read-item","description":"Read item alias","inputSchema":{"type":"object"}},
    ]}
    try:
        scan_mcp_snapshot(snap)
        assert False, "expected canonical identity collision"
    except ValueError as exc:
        assert "Duplicate canonical capability identity" in str(exc)


def test_compile_rejects_inventory_with_security_analysis_tampering():
    inv=scan_mcp_snapshot(SNAP)
    inv["capabilities"][1]["effect"]="read"
    try:
        compile_capsule(
            inv,
            {"capabilities":["mcp:demo:create_issue"]},
            {"default":"allow"},
            now=100,
        )
        assert False, "expected invalid inventory integrity"
    except ValueError as exc:
        assert "Invalid inventory integrity" in str(exc)
