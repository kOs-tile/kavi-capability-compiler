import copy

import pytest

import kavi_capability_compiler as kcc


def _inventory(*, add_delete=False, changed_schema=False):
    update_properties={
        "id":{"type":"string"},
        "value":{"type":"string"},
        "force":{"type":"boolean"},
    }
    if changed_schema:
        update_properties["scope"]={"type":"string"}
    tools=[
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
                "properties":update_properties,
                "required":["id","value"],
            },
        },
    ]
    if add_delete:
        tools.append({
            "name":"delete_record",
            "description":"Delete record",
            "input_schema":{
                "type":"object",
                "properties":{"id":{"type":"string"}},
                "required":["id"],
            },
        })
    return kcc.scan_manifest(kcc.adapt_capabilities(
        "generic",
        {"tools":tools},
        namespace="records",
    ))


def _read_capsule(inv):
    cid=next(x["id"] for x in inv["capabilities"] if x["name"]=="get_record")
    cap=kcc.compile_capsule(
        inv,
        {"task":"read one record","capabilities":[cid],"ttl_seconds":60},
        {"default":"allow"},
        now=100,
    )
    return cap,cid


def test_inventory_bound_guard_rejects_schema_drift_before_dispatch():
    original=_inventory()
    cap,cid=_read_capsule(original)
    drifted=_inventory(changed_schema=True)
    calls=[]

    guard=kcc.Guard.from_capsule(cap,inventory=drifted)
    with pytest.raises(kcc.AuthorityDenied) as exc:
        guard.dispatch_sync(
            cid,
            lambda params: calls.append(dict(params)),
            parameters={"id":"1"},
            now=101,
        )

    assert exc.value.reason=="inventory_drift"
    assert calls==[]


def test_inventory_bound_guard_rejects_capability_added_after_compile():
    original=_inventory()
    cap,cid=_read_capsule(original)
    expanded=_inventory(add_delete=True)

    decision=kcc.Guard.from_capsule(cap,inventory=expanded).authorize(
        cid,parameters={"id":"1"},now=101
    )
    assert decision["allowed"] is False
    assert decision["reason"]=="inventory_drift"


def test_inventory_binding_rejects_tampered_inventory_digest():
    original=_inventory()
    cap,cid=_read_capsule(original)
    tampered=copy.deepcopy(original)
    tampered["capabilities"].append(copy.deepcopy(tampered["capabilities"][0]))

    decision=kcc.Guard.from_capsule(cap,inventory=tampered).authorize(
        cid,parameters={"id":"1"},now=101
    )
    assert decision["allowed"] is False
    assert decision["reason"]=="invalid_inventory_integrity"


def test_parameter_constraints_reject_undeclared_runtime_keys():
    inv=_inventory()
    cid=next(x["id"] for x in inv["capabilities"] if x["name"]=="update_record")
    cap=kcc.compile_capsule(
        inv,
        {
            "task":"update one record without force",
            "capabilities":[cid],
            "capability_constraints":{
                cid:{
                    "parameters":{
                        "id":"REC-1",
                        "value":{},
                    }
                }
            },
        },
        {"default":"allow"},
        now=100,
    )
    guard=kcc.Guard.from_capsule(cap,inventory=inv)

    assert guard.authorize(
        cid,
        parameters={"id":"REC-1","value":"ok"},
        now=101,
    )["allowed"]

    denied=guard.authorize(
        cid,
        parameters={"id":"REC-1","value":"ok","force":True},
        now=101,
    )
    assert denied["allowed"] is False
    assert denied["reason"]=="parameter_not_granted:force"


def test_no_parameter_constraints_preserves_unbounded_parameter_names():
    inv=_inventory()
    cid=next(x["id"] for x in inv["capabilities"] if x["name"]=="update_record")
    cap=kcc.compile_capsule(inv,{"capabilities":[cid]},{"default":"allow"},now=100)
    decision=kcc.Guard.from_capsule(cap,inventory=inv).authorize(
        cid,
        parameters={"id":"REC-1","value":"ok","force":True},
        now=101,
    )
    assert decision["allowed"] is True


def test_inventory_bound_signed_guard_rejects_drift():
    from kavi_capability_compiler.signing import generate_ed25519_keypair, sign_capsule

    original=_inventory()
    cap,cid=_read_capsule(original)
    private,public=generate_ed25519_keypair()
    envelope=sign_capsule(cap,private,key_id="root-1")
    drifted=_inventory(add_delete=True)

    guard=kcc.Guard.from_signed(
        envelope,
        {"root-1":public},
        inventory=drifted,
        now=101,
    )
    decision=guard.authorize(cid,parameters={"id":"1"},now=101)
    assert decision["allowed"] is False
    assert decision["reason"]=="inventory_drift"
