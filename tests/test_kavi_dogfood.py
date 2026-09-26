import json
from pathlib import Path

from kavi_capability_compiler.core import authorize_call, compile_capsule
from kavi_capability_compiler.kavi_dispatch import scan_kavi_dispatch_contract

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
