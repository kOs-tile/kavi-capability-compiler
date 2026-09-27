import copy
import json

import kavi_capability_compiler as kcc
from kavi_capability_compiler.signing import (
    generate_ed25519_keypair,
    sign_capsule,
    verify_signed_capsule,
)


def inventory(*, changed=False, added=False):
    update_properties={
        "id":{"type":"string"},
        "value":{"type":"string"},
        "force":{"type":"boolean"},
    }
    if changed:
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
    if added:
        tools.append({
            "name":"delete_record",
            "description":"Delete record",
            "input_schema":{
                "type":"object",
                "properties":{"id":{"type":"string"}},
                "required":["id"],
            },
        })
    manifest=kcc.adapt_capabilities("generic",{"tools":tools},namespace="records")
    return manifest,kcc.scan_manifest(manifest)


def ids(inv):
    return {x["name"]:x["id"] for x in inv["capabilities"]}


def case(name, passed, evidence):
    return {
        "name":name,
        "classification":"enforced",
        "passed":bool(passed),
        "evidence":evidence,
    }


manifest,inv=inventory()
cid=ids(inv)["get_record"]
cap=kcc.compile_capsule(
    inv,
    {"task":"read one record","capabilities":[cid],"ttl_seconds":60},
    {"default":"allow"},
    now=100,
)
cases=[]

tampered=copy.deepcopy(cap)
tampered["task"]="tampered"
decision=kcc.authorize_call(tampered,cid,parameters={"id":"1"},now=101,inventory=inv)
cases.append(case(
    "capsule_tampering",
    not decision["allowed"] and decision["reason"]=="invalid_capsule_integrity",
    decision["reason"],
))

manifest_tampered=copy.deepcopy(manifest)
manifest_tampered["capabilities"][0]["description"]="tampered"
manifest_blocked=False
try:
    kcc.scan_manifest(manifest_tampered)
except ValueError:
    manifest_blocked=True
cases.append(case("manifest_tampering",manifest_blocked,"fingerprint_mismatch"))

namespace_manifest=kcc.adapt_capabilities(
    "generic",
    {"tools":[
        {"namespace":"github","name":"search","description":"Search GitHub","input_schema":{"type":"object"}},
        {"namespace":"slack","name":"search","description":"Search Slack","input_schema":{"type":"object"}},
    ]},
    namespace="fallback",
)
namespace_inv=kcc.scan_manifest(namespace_manifest)
namespace_ids=sorted(x["id"] for x in namespace_inv["capabilities"])
cases.append(case(
    "namespace_collision",
    namespace_ids==["kcc:github:search","kcc:slack:search"],
    namespace_ids,
))

_,drifted=inventory(changed=True)
decision=kcc.Guard.from_capsule(cap,inventory=drifted).authorize(
    cid,parameters={"id":"1"},now=101
)
cases.append(case(
    "schema_drift",
    not decision["allowed"] and decision["reason"]=="inventory_drift",
    decision["reason"],
))

expired=kcc.Guard.from_capsule(cap,inventory=inv).authorize(
    cid,parameters={"id":"1"},now=1000
)
cases.append(case(
    "expired_capsule",
    not expired["allowed"] and expired["reason"]=="expired",
    expired["reason"],
))

private,public=generate_ed25519_keypair()
_,wrong_public=generate_ed25519_keypair()
envelope=sign_capsule(cap,private,key_id="root-1")
wrong_key=verify_signed_capsule(envelope,{"root-1":wrong_public},now=101)
cases.append(case("wrong_signing_key",not wrong_key["valid"],wrong_key["checks"]))

update_id=ids(inv)["update_record"]
approval_cap=kcc.compile_capsule(inv,{"capabilities":[update_id]},{"default":"approval"},now=100)
approval_calls=[]
approval_blocked=False
try:
    kcc.Guard.from_capsule(approval_cap,inventory=inv).dispatch_sync(
        update_id,
        lambda params: approval_calls.append(dict(params)),
        parameters={"id":"1","value":"x"},
        now=101,
    )
except kcc.ApprovalRequired:
    approval_blocked=True
cases.append(case(
    "approval_bypass_through_guard",
    approval_blocked and approval_calls==[],
    {"dispatcher_calls":len(approval_calls)},
))

lock=kcc.inventory_lock(inv)
lock_diff=kcc.diff_inventory_lock(lock,drifted)
cases.append(case(
    "stale_inventory_lock",
    not lock_diff["clean"] and bool(lock_diff["changed"]),
    lock_diff,
))

_,expanded=inventory(added=True)
added_decision=kcc.Guard.from_capsule(cap,inventory=expanded).authorize(
    cid,parameters={"id":"1"},now=101
)
cases.append(case(
    "capability_added_after_compile",
    not added_decision["allowed"] and added_decision["reason"]=="inventory_drift",
    added_decision["reason"],
))

bounded_cap=kcc.compile_capsule(
    inv,
    {
        "capabilities":[update_id],
        "capability_constraints":{
            update_id:{
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
parameter_decision=kcc.Guard.from_capsule(bounded_cap,inventory=inv).authorize(
    update_id,
    parameters={"id":"REC-1","value":"ok","force":True},
    now=101,
)
cases.append(case(
    "parameter_bound_bypass",
    not parameter_decision["allowed"] and parameter_decision["reason"]=="parameter_not_granted:force",
    parameter_decision["reason"],
))

unsupported_parameter_rule_blocked=False
unsupported_parameter_rule_evidence=None
try:
    kcc.compile_capsule(
        inv,
        {
            "capabilities":[update_id],
            "capability_constraints":{
                update_id:{
                    "parameters":{
                        "id":{"type":"string","maxLength":8},
                        "value":{},
                    }
                }
            },
        },
        {"default":"allow"},
        now=100,
    )
except ValueError as exc:
    unsupported_parameter_rule_evidence=str(exc)
    unsupported_parameter_rule_blocked="Unsupported parameter rule" in str(exc)
cases.append(case(
    "unsupported_parameter_rule_rejected",
    unsupported_parameter_rule_blocked,
    unsupported_parameter_rule_evidence,
))

replay_guard=kcc.Guard.from_capsule(cap,inventory=inv)
replay_first=replay_guard.authorize(cid,parameters={"id":"1"},now=101)
replay_second=replay_guard.authorize(cid,parameters={"id":"1"},now=102)

direct_dispatch_calls=[]
def host_dispatch(params):
    direct_dispatch_calls.append(dict(params))
    return {"ok":True}
host_dispatch({"id":"direct"})

boundaries={
    "replay":{
        "classification":"host_responsibility",
        "observed_valid_before_expiry":bool(replay_first["allowed"] and replay_second["allowed"]),
        "requirement":"host state is required for one-shot or distributed replay prevention",
    },
    "direct_dispatcher_bypass":{
        "classification":"outside_kcc_mediation",
        "observed_direct_host_call":len(direct_dispatch_calls)==1,
        "requirement":"host must route protected calls through Guard",
    },
}

enforced=[x for x in cases if x["classification"]=="enforced"]
result={
    "benchmark":"kcc.adversarial-sdk.v1",
    "enforced_cases":len(enforced),
    "all_enforced_cases_pass":all(x["passed"] for x in enforced),
    "cases":cases,
    "boundaries":boundaries,
}
print(json.dumps(result,indent=2,sort_keys=True))
