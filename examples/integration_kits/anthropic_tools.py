"""Anthropic definitions -> KCC -> inventory-bound Guard -> host dispatcher.

This example intentionally does not import the Anthropic SDK. KCC consumes the
capability-definition shape and remains independent of the host runtime.
"""
import kavi_capability_compiler as kcc

GET_SCHEMA={
    "type":"object",
    "properties":{"id":{"type":"string"}},
    "required":["id"],
}
UPDATE_SCHEMA={
    "type":"object",
    "properties":{"id":{"type":"string"},"value":{"type":"string"}},
    "required":["id","value"],
}

payload={
    "tools":[
        {"name":"get_record","description":"Get a record by ID","input_schema":GET_SCHEMA},
        {"name":"update_record","description":"Update a record","input_schema":UPDATE_SCHEMA},
    ]
}

manifest=kcc.adapt_capabilities("anthropic",payload,namespace="records")
inventory=kcc.scan_manifest(manifest)
ids={item["name"]:item["id"] for item in inventory["capabilities"]}

capsule=kcc.compile_capsule(
    inventory,
    {
        "task":"Read one record without mutation",
        "capabilities":[ids["get_record"]],
        "capability_constraints":{
            ids["get_record"]:{
                "parameters":{
                    "id":{"required":True,"type":"string"},
                }
            }
        },
    },
    {"default":"allow"},
    now=100,
)

guard=kcc.Guard.from_capsule(capsule,inventory=inventory)
dispatcher_calls=[]

def existing_host_dispatcher(params):
    dispatcher_calls.append(dict(params))
    return {"id":params["id"],"value":"example"}

result=guard.dispatch_sync(
    ids["get_record"],
    existing_host_dispatcher,
    parameters={"id":"REC-1"},
    now=101,
)
assert result["executed"] is True
assert result["result"]["id"]=="REC-1"

before=len(dispatcher_calls)
try:
    guard.dispatch_sync(
        ids["update_record"],
        existing_host_dispatcher,
        parameters={"id":"REC-1","value":"blocked"},
        now=101,
    )
    raise AssertionError("outside-capsule mutation reached dispatcher")
except kcc.AuthorityDenied as exc:
    assert exc.reason=="capability_not_granted"

assert len(dispatcher_calls)==before
print("KCC_KIT_ANTHROPIC: PASS")
