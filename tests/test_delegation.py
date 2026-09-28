import copy

import pytest

import kavi_capability_compiler as kcc
from kavi_capability_compiler.core import digest


def _inventory():
    manifest=kcc.adapt_capabilities(
        "generic",
        {"tools":[
            {
                "name":"update_record",
                "description":"Update record",
                "input_schema":{
                    "type":"object",
                    "properties":{
                        "amount":{"type":"number"},
                        "mode":{"type":"string"},
                        "note":{"type":"string"},
                    },
                },
            },
            {
                "name":"delete_record",
                "description":"Delete record",
                "input_schema":{
                    "type":"object",
                    "properties":{"id":{"type":"string"}},
                },
            },
        ]},
        namespace="records",
    )
    return kcc.scan_manifest(manifest)


def _ids(inv):
    return {x["name"]:x["id"] for x in inv["capabilities"]}


def _parent(inv, *, constraints=None, decision="allow", now=100):
    cid=_ids(inv)["update_record"]
    intent={"task":"parent","capabilities":[cid],"ttl_seconds":600}
    if constraints is not None:
        intent["capability_constraints"]={cid:constraints}
    return kcc.compile_capsule(inv,intent,{"default":decision},now=now)


def _request(parent, cid, *, constraints_marker=None, ttl=300, task="child"):
    item={"id":cid}
    if constraints_marker is not None:
        item["constraints"]=constraints_marker
    return {
        "version":kcc.DELEGATION_REQUEST_VERSION,
        "parent_capsule_id":parent["capsule_id"],
        "task":task,
        "ttl_seconds":ttl,
        "capabilities":[item],
    }


def _rehash_capsule(cap):
    body=copy.deepcopy(cap)
    body.pop("capsule_id",None)
    cap["capsule_id"]=digest(body)


def _rehash_envelope(env):
    body=copy.deepcopy(env)
    body.pop("envelope_id",None)
    env["envelope_id"]=digest(body)


def test_valid_delegation_narrows_capability_operations_parameters_and_lifetime():
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    parent=_parent(
        inv,
        constraints={
            "operations":["preview","update"],
            "parameters":{
                "amount":{"required":True,"type":"number","min":0,"max":100},
                "mode":{"type":"string","enum":["safe","fast"]},
                "note":{"type":"string","max_length":20,"pattern":"[a-z]+"},
            },
        },
    )
    req=_request(
        parent,
        cid,
        constraints_marker={
            "operations":["update"],
            "parameters":{
                "amount":{"required":True,"type":"integer","min":10,"max":50},
                "mode":{"type":"string","enum":["safe"]},
            },
        },
        ttl=120,
    )

    env=kcc.attenuate_capsule(parent,req,inv,now=110)
    child=env["child_capsule"]

    assert env["version"]==kcc.DELEGATED_CAPSULE_VERSION
    assert child["version"]==kcc.CAPSULE_VERSION
    assert child["issued_at"]==110
    assert child["expires_at"]==230
    assert child["intent_digest"]==env["attenuation_request_digest"]
    assert child["policy_digest"]==parent["policy_digest"]
    assert child["approvals"]==[]
    assert child["denials"]==[]
    assert child["grants"][0]["fingerprint"]==parent["grants"][0]["fingerprint"]
    assert kcc.verify_delegated_capsule(env,parent,inv,now=111)["valid"] is True


def test_missing_child_constraints_inherit_parent_constraints():
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    parent=_parent(inv,constraints={"operations":["update"],"parameters":{"mode":{"enum":["safe"]}}})
    env=kcc.attenuate_capsule(parent,_request(parent,cid),inv,now=110)
    assert env["child_capsule"]["grants"][0]["constraints"]==parent["grants"][0]["constraints"]


def test_operation_scope_cannot_widen():
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    parent=_parent(inv,constraints={"operations":["update"]})
    with pytest.raises(ValueError,match="operation"):
        kcc.attenuate_capsule(
            parent,
            _request(parent,cid,constraints_marker={"operations":["update","delete"]}),
            inv,
            now=110,
        )


def test_restricted_parent_cannot_delegate_unrestricted_operations():
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    parent=_parent(inv,constraints={"operations":["update"]})
    with pytest.raises(ValueError,match="operation"):
        kcc.attenuate_capsule(
            parent,
            _request(parent,cid,constraints_marker={}),
            inv,
            now=110,
        )


@pytest.mark.parametrize(
    "child_rule",
    [
        {"required":True,"type":"number","min":-1,"max":100},
        {"required":True,"type":"number","min":0,"max":101},
        {"required":False,"type":"number","min":0,"max":100},
    ],
)
def test_numeric_or_required_parameter_scope_cannot_widen(child_rule):
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    parent=_parent(
        inv,
        constraints={"parameters":{"amount":{"required":True,"type":"number","min":0,"max":100}}},
    )
    with pytest.raises(ValueError,match="parameter"):
        kcc.attenuate_capsule(
            parent,
            _request(parent,cid,constraints_marker={"parameters":{"amount":child_rule}}),
            inv,
            now=110,
        )


def test_number_parent_can_narrow_to_integer_child():
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    parent=_parent(inv,constraints={"parameters":{"amount":{"type":"number"}}})
    env=kcc.attenuate_capsule(
        parent,
        _request(parent,cid,constraints_marker={"parameters":{"amount":{"type":"integer"}}}),
        inv,
        now=110,
    )
    assert kcc.verify_delegated_capsule(env,parent,inv,now=111)["valid"] is True


def test_enum_must_be_subset():
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    parent=_parent(inv,constraints={"parameters":{"mode":{"type":"string","enum":["safe","fast"]}}})
    good=kcc.attenuate_capsule(
        parent,
        _request(parent,cid,constraints_marker={"parameters":{"mode":{"type":"string","enum":["safe"]}}}),
        inv,
        now=110,
    )
    assert kcc.verify_delegated_capsule(good,parent,inv,now=111)["valid"] is True
    with pytest.raises(ValueError,match="parameter"):
        kcc.attenuate_capsule(
            parent,
            _request(parent,cid,constraints_marker={"parameters":{"mode":{"type":"string","enum":["safe","other"]}}}),
            inv,
            now=110,
        )


def test_max_length_can_only_tighten_and_pattern_must_match():
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    parent=_parent(inv,constraints={"parameters":{"note":{"type":"string","max_length":20,"pattern":"[a-z]+"}}})
    good=kcc.attenuate_capsule(
        parent,
        _request(parent,cid,constraints_marker={"parameters":{"note":{"type":"string","max_length":10,"pattern":"[a-z]+"}}}),
        inv,
        now=110,
    )
    assert kcc.verify_delegated_capsule(good,parent,inv,now=111)["valid"] is True

    for child in (
        {"type":"string","max_length":21,"pattern":"[a-z]+"},
        {"type":"string","max_length":10,"pattern":".+"},
    ):
        with pytest.raises(ValueError,match="parameter"):
            kcc.attenuate_capsule(
                parent,
                _request(parent,cid,constraints_marker={"parameters":{"note":child}}),
                inv,
                now=110,
            )


@pytest.mark.parametrize(
    "parent_rule,child_value",
    [
        ({"type":"string","enum":["safe","fast"]},"safe"),
        ({"type":"integer"},1),
        ({"required":True,"type":"string","enum":["safe"]},"safe"),
    ],
)
def test_structured_parent_to_exact_scalar_fails_closed(parent_rule,child_value):
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    key="amount" if parent_rule.get("type")=="integer" else "mode"
    parent=_parent(inv,constraints={"parameters":{key:parent_rule}})
    with pytest.raises(ValueError,match="parameter"):
        kcc.attenuate_capsule(
            parent,
            _request(parent,cid,constraints_marker={"parameters":{key:child_value}}),
            inv,
            now=110,
        )


def test_python_equality_alias_cannot_widen_typed_parent():
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    parent=_parent(inv,constraints={"parameters":{"amount":{"type":"integer"}}})
    with pytest.raises(ValueError,match="parameter"):
        kcc.attenuate_capsule(
            parent,
            _request(parent,cid,constraints_marker={"parameters":{"amount":1}}),
            inv,
            now=110,
        )


def test_parent_parameter_map_cannot_be_removed_or_gain_unknown_key():
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    parent=_parent(inv,constraints={"parameters":{"mode":{"enum":["safe"]}}})

    with pytest.raises(ValueError,match="parameter"):
        kcc.attenuate_capsule(parent,_request(parent,cid,constraints_marker={}),inv,now=110)

    with pytest.raises(ValueError,match="parameter"):
        kcc.attenuate_capsule(
            parent,
            _request(parent,cid,constraints_marker={"parameters":{"note":{"max_length":3}}}),
            inv,
            now=110,
        )


def test_non_granted_parent_authority_cannot_be_upgraded():
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    parent=_parent(inv,decision="approval")
    with pytest.raises(ValueError,match="parent grant"):
        kcc.attenuate_capsule(parent,_request(parent,cid),inv,now=110)


def test_child_expiry_is_clamped_to_parent_expiry():
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    parent=_parent(inv,now=100)
    env=kcc.attenuate_capsule(parent,_request(parent,cid,ttl=86400),inv,now=650)
    assert env["child_capsule"]["expires_at"]==parent["expires_at"]


def test_expired_parent_cannot_delegate():
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    parent=_parent(inv,now=100)
    with pytest.raises(ValueError,match="parent capsule"):
        kcc.attenuate_capsule(parent,_request(parent,cid),inv,now=parent["expires_at"])


def test_rehashed_operation_widening_still_fails_verification():
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    parent=_parent(inv,constraints={"operations":["update"]})
    env=kcc.attenuate_capsule(parent,_request(parent,cid),inv,now=110)

    env["child_capsule"]["grants"][0]["constraints"]["operations"]=["update","delete"]
    _rehash_capsule(env["child_capsule"])
    _rehash_envelope(env)

    result=kcc.verify_delegated_capsule(env,parent,inv,now=111)
    assert result["valid"] is False
    assert {x["name"] for x in result["checks"] if not x["ok"]} >= {"attenuation"}


def test_rehashed_capability_addition_still_fails_verification():
    inv=_inventory()
    ids=_ids(inv)
    parent=_parent(inv)
    env=kcc.attenuate_capsule(parent,_request(parent,ids["update_record"]),inv,now=110)

    extra=next(x for x in inv["capabilities"] if x["id"]==ids["delete_record"])
    env["child_capsule"]["grants"].append({
        "id":extra["id"],
        "fingerprint":extra["fingerprint"],
        "effect":extra["effect"],
        "risk_flags":extra["analysis"]["risk_flags"],
        "constraints":{},
    })
    _rehash_capsule(env["child_capsule"])
    _rehash_envelope(env)

    assert kcc.verify_delegated_capsule(env,parent,inv,now=111)["valid"] is False


def test_child_approval_or_denial_state_is_not_delegated():
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    parent=_parent(inv)
    env=kcc.attenuate_capsule(parent,_request(parent,cid),inv,now=110)

    env["child_capsule"]["approvals"]=[copy.deepcopy(env["child_capsule"]["grants"][0])]
    env["child_capsule"]["status"]="approval_required"
    _rehash_capsule(env["child_capsule"])
    _rehash_envelope(env)

    result=kcc.verify_delegated_capsule(env,parent,inv,now=111)
    assert result["valid"] is False


def test_inventory_drift_invalidates_delegation_verification():
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    parent=_parent(inv)
    env=kcc.attenuate_capsule(parent,_request(parent,cid),inv,now=110)

    drift=copy.deepcopy(inv)
    target=next(x for x in drift["capabilities"] if x["id"]==cid)
    target["fingerprint"]="0"*64
    body=copy.deepcopy(drift)
    body.pop("digest",None)
    drift["digest"]=digest(body)

    assert kcc.verify_delegated_capsule(env,parent,drift,now=111)["valid"] is False


def test_tampered_envelope_integrity_fails_closed():
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    parent=_parent(inv)
    env=kcc.attenuate_capsule(parent,_request(parent,cid),inv,now=110)
    env["provenance"]["kind"]="other"
    result=kcc.verify_delegated_capsule(env,parent,inv,now=111)
    assert result["valid"] is False
    assert any(x["name"]=="integrity" and not x["ok"] for x in result["checks"])


def test_unsupported_child_parameter_rule_is_rejected():
    inv=_inventory()
    cid=_ids(inv)["update_record"]
    parent=_parent(inv)
    with pytest.raises(ValueError,match="Unsupported parameter rule"):
        kcc.attenuate_capsule(
            parent,
            _request(parent,cid,constraints_marker={"parameters":{"mode":{"maxLength":3}}}),
            inv,
            now=110,
        )
