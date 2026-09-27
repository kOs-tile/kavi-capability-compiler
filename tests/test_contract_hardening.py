import copy

import pytest

import kavi_capability_compiler as kcc
from kavi_capability_compiler.core import digest
from kavi_capability_compiler.signing import generate_ed25519_keypair, sign_capsule


def _inventory():
    manifest=kcc.adapt_capabilities(
        "generic",
        {"tools":[
            {
                "name":"get_record",
                "description":"Get record",
                "input_schema":{
                    "type":"object",
                    "properties":{"id":{"type":"string"}},
                    "required":["id"],
                },
            },
            {
                "name":"update_record",
                "description":"Update record",
                "input_schema":{
                    "type":"object",
                    "properties":{
                        "id":{"type":"string"},
                        "value":{"type":"string"},
                    },
                    "required":["id","value"],
                },
            },
        ]},
        namespace="records",
    )
    return kcc.scan_manifest(manifest)


def _rehash_capsule(capsule):
    body=copy.deepcopy(capsule)
    body.pop("capsule_id",None)
    capsule["capsule_id"]=digest(body)


def test_v1_inventory_capsule_and_lock_contracts_are_emitted():
    inv=_inventory()
    cid=next(x["id"] for x in inv["capabilities"] if x["name"]=="get_record")
    cap=kcc.compile_capsule(inv,{"capabilities":[cid]},{"default":"allow"},now=100)
    lock=kcc.inventory_lock(inv)

    assert inv["version"]=="kcc.inventory.v1"
    assert cap["version"]=="kcc.capsule.v1"
    assert cap["fail_closed"] is True
    assert lock["version"]=="kcc.inventory-lock.v1"


def test_compiler_and_lock_reject_legacy_inventory_contracts():
    inv=_inventory()
    legacy=copy.deepcopy(inv)
    legacy["version"]="kcc.inventory.v0"

    with pytest.raises(ValueError,match="Unsupported inventory contract"):
        kcc.compile_capsule(legacy,{"capabilities":[]},{"default":"deny"},now=100)

    with pytest.raises(ValueError,match="Unsupported inventory contract"):
        kcc.inventory_lock(legacy)


def test_inventory_lock_diff_rejects_legacy_lock_contract():
    inv=_inventory()
    lock=kcc.inventory_lock(inv)
    legacy=copy.deepcopy(lock)
    legacy["version"]="kcc.inventory-lock.v0"

    with pytest.raises(ValueError,match="Unsupported inventory lock contract"):
        kcc.diff_inventory_lock(legacy,inv)


def test_recomputed_integrity_cannot_bypass_capsule_version():
    inv=_inventory()
    cid=next(x["id"] for x in inv["capabilities"] if x["name"]=="get_record")
    cap=kcc.compile_capsule(inv,{"capabilities":[cid]},{"default":"allow"},now=100)

    cap["version"]="kcc.capsule.v0"
    _rehash_capsule(cap)

    decision=kcc.authorize_call(cap,cid,parameters={"id":"1"},now=101)
    assert decision["allowed"] is False
    assert decision["reason"]=="unsupported_capsule_version"


def test_recomputed_integrity_cannot_bypass_fail_closed_marker():
    inv=_inventory()
    cid=next(x["id"] for x in inv["capabilities"] if x["name"]=="get_record")
    cap=kcc.compile_capsule(inv,{"capabilities":[cid]},{"default":"allow"},now=100)

    cap["fail_closed"]=False
    _rehash_capsule(cap)

    decision=kcc.authorize_call(cap,cid,parameters={"id":"1"},now=101)
    assert decision["allowed"] is False
    assert decision["reason"]=="fail_closed_required"


def test_verify_capsule_reports_contract_checks():
    inv=_inventory()
    cid=next(x["id"] for x in inv["capabilities"] if x["name"]=="get_record")
    cap=kcc.compile_capsule(inv,{"capabilities":[cid]},{"default":"allow"},now=100)
    result=kcc.verify_capsule(cap,inv,now=101)
    checks={x["name"]:x["ok"] for x in result["checks"]}

    assert result["valid"] is True
    assert checks["version"] is True
    assert checks["fail_closed"] is True
    assert checks["inventory_version"] is True


def test_exception_semantics_are_stable_and_pre_dispatch():
    inv=_inventory()
    ids={x["name"]:x["id"] for x in inv["capabilities"]}
    calls=[]

    approval=kcc.compile_capsule(
        inv,
        {"capabilities":[ids["update_record"]]},
        {"default":"approval"},
        now=100,
    )
    with pytest.raises(kcc.ApprovalRequired) as exc:
        kcc.Guard.from_capsule(approval).dispatch_sync(
            ids["update_record"],
            lambda params: calls.append(params),
            parameters={"id":"1","value":"x"},
            now=101,
        )
    assert exc.value.reason=="approval_required"
    assert exc.value.decision["reason"]=="approval_required"
    assert str(exc.value)=="approval_required"
    assert calls==[]

    denied=kcc.compile_capsule(
        inv,
        {"capabilities":[ids["update_record"]]},
        {"default":"deny"},
        now=100,
    )
    with pytest.raises(kcc.CapabilityDenied) as exc:
        kcc.Guard.from_capsule(denied).dispatch_sync(
            ids["update_record"],
            lambda params: calls.append(params),
            parameters={"id":"1","value":"x"},
            now=101,
        )
    assert exc.value.reason=="capability_denied"
    assert calls==[]

    read_only=kcc.compile_capsule(
        inv,
        {"capabilities":[ids["get_record"]]},
        {"default":"allow"},
        now=100,
    )
    with pytest.raises(kcc.AuthorityDenied) as exc:
        kcc.Guard.from_capsule(read_only).dispatch_sync(
            ids["update_record"],
            lambda params: calls.append(params),
            parameters={"id":"1","value":"x"},
            now=101,
        )
    assert type(exc.value) is kcc.AuthorityDenied
    assert exc.value.reason=="capability_not_granted"
    assert calls==[]


def test_signing_rejects_rehashed_unsupported_capsule_contract():
    inv=_inventory()
    cid=next(x["id"] for x in inv["capabilities"] if x["name"]=="get_record")
    cap=kcc.compile_capsule(inv,{"capabilities":[cid]},{"default":"allow"},now=100)
    private,_=generate_ed25519_keypair()

    cap["version"]="kcc.capsule.v0"
    _rehash_capsule(cap)
    with pytest.raises(ValueError,match="Unsupported capsule contract"):
        sign_capsule(cap,private,key_id="test-key")


def test_signing_rejects_rehashed_non_fail_closed_capsule():
    inv=_inventory()
    cid=next(x["id"] for x in inv["capabilities"] if x["name"]=="get_record")
    cap=kcc.compile_capsule(inv,{"capabilities":[cid]},{"default":"allow"},now=100)
    private,_=generate_ed25519_keypair()

    cap["fail_closed"]=False
    _rehash_capsule(cap)
    with pytest.raises(ValueError,match="fail_closed=true"):
        sign_capsule(cap,private,key_id="test-key")
