import json
from pathlib import Path

from kavi_capability_compiler.core import authorize_call, compile_capsule
from case_studies.kavi.kavi_dispatch import scan_kavi_dispatch_contract

FIXTURE=Path(__file__).parents[1]/"benchmark"/"kavi_dogfood"/"dispatch_contract.json"


def _inventory():
    raw=json.loads(FIXTURE.read_text())
    s=raw["source"]
    return scan_kavi_dispatch_contract(
        raw["contract"],
        source_repository=s["repository"],
        source_path=s["path"],
        source_sha=s["sha"],
    )


def test_kavi_adapter_preserves_authoritative_surface_and_provenance():
    inv=_inventory()
    assert len(inv["capabilities"])==5
    assert inv["provenance"]["sha"]=="80f521a9aba225bbc5abcb815feae24569fa8098"
    by_name={x["name"]:x for x in inv["capabilities"]}
    assert by_name["get_operator_snapshot"]["effect"]=="read"
    assert by_name["enqueue_task"]["effect"]=="write"
    assert "declared_mutation" in by_name["approve_task"]["analysis"]["risk_flags"]
    assert "approval_contract_required" in by_name["approve_task"]["analysis"]["risk_flags"]


def test_read_only_kavi_capsule_blocks_outside_control_plane_authority():
    inv=_inventory()
    ids={x["name"]:x["id"] for x in inv["capabilities"]}
    intent={
        "task":"Read the current KAVI operator snapshot without mutating execution state",
        "ttl_seconds":300,
        "capabilities":[ids["get_operator_snapshot"]],
    }
    policy={
        "default":"deny",
        "allow":[{"capabilities":[ids["get_operator_snapshot"]]}],
        "deny":[{"effects":["write","delete","execute","deploy","financial","external_message"]}],
    }
    cap=compile_capsule(inv,intent,policy,now=100)
    assert cap["status"]=="ready"
    assert [x["id"] for x in cap["grants"]]==[ids["get_operator_snapshot"]]
    assert authorize_call(cap,ids["get_operator_snapshot"],parameters={},now=101)["allowed"]
    assert authorize_call(cap,ids["enqueue_task"],parameters={},now=101)["reason"]=="capability_not_granted"
    assert authorize_call(cap,ids["approve_task"],parameters={},now=101)["reason"]=="capability_not_granted"


def test_provenance_revision_without_authority_change_does_not_create_capability_drift():
    raw=json.loads(FIXTURE.read_text())
    s=raw["source"]
    a=scan_kavi_dispatch_contract(raw["contract"],source_repository=s["repository"],source_path=s["path"],source_sha=s["sha"])
    b=scan_kavi_dispatch_contract(raw["contract"],source_repository=s["repository"],source_path=s["path"],source_sha="different-source-revision")
    assert a["digest"]==b["digest"]
    assert [x["fingerprint"] for x in a["capabilities"]]==[x["fingerprint"] for x in b["capabilities"]]


def test_declared_authority_change_changes_only_affected_capability():
    raw=json.loads(FIXTURE.read_text())
    s=raw["source"]
    a=scan_kavi_dispatch_contract(raw["contract"],source_repository=s["repository"],source_path=s["path"],source_sha=s["sha"])
    changed=json.loads(json.dumps(raw["contract"]))
    for tool in changed["tools"]:
        if tool["name"]=="get_task_status":
            tool["write"]=True
    b=scan_kavi_dispatch_contract(changed,source_repository=s["repository"],source_path=s["path"],source_sha="new-revision")
    afp={x["name"]:x["fingerprint"] for x in a["capabilities"]}
    bfp={x["name"]:x["fingerprint"] for x in b["capabilities"]}
    changed_names=sorted(name for name in afp if afp[name]!=bfp[name])
    assert changed_names==["get_task_status"]
