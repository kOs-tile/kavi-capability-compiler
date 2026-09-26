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
