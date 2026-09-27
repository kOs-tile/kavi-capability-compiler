"""OpenAPI operations -> KCC -> inventory-bound Guard -> host dispatcher.

No OpenAPI client framework is required by KCC. The host keeps its existing HTTP
client/dispatcher and places Guard immediately before that call.
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

document={
    "openapi":"3.1.0",
    "paths":{
        "/records/get":{
            "post":{
                "operationId":"get_record",
                "description":"Get a record by ID",
                "requestBody":{"content":{"application/json":{"schema":GET_SCHEMA}}},
            }
        },
        "/records/update":{
            "post":{
                "operationId":"update_record",
                "description":"Update a record",
                "requestBody":{"content":{"application/json":{"schema":UPDATE_SCHEMA}}},
            }
        },
    },
}

manifest=kcc.adapt_capabilities("openapi",document,namespace="records")
inventory=kcc.scan_manifest(manifest)
ids={item["name"]:item["id"] for item in inventory["capabilities"]}
capsule=kcc.compile_capsule(
    inventory,
    {
        "task":"Read one record without mutation",
        "capabilities":[ids["get_record"]],
        "capability_constraints":{
            ids["get_record"]:{
                "parameters":{"id":{"required":True,"type":"string"}}
            }
        },
    },
    {"default":"allow"},
    now=100,
)
guard=kcc.Guard.from_capsule(capsule,inventory=inventory)
dispatcher_calls=[]

def existing_http_dispatcher(params):
    dispatcher_calls.append(dict(params))
    return {"status":200,"json":{"id":params["id"],"value":"example"}}

result=guard.dispatch_sync(
    ids["get_record"],
    existing_http_dispatcher,
    parameters={"id":"REC-1"},
    now=101,
)
assert result["result"]["status"]==200

before=len(dispatcher_calls)
try:
    guard.dispatch_sync(
        ids["update_record"],
        existing_http_dispatcher,
        parameters={"id":"REC-1","value":"blocked"},
        now=101,
    )
    raise AssertionError("outside-capsule mutation reached dispatcher")
except kcc.AuthorityDenied as exc:
    assert exc.reason=="capability_not_granted"

assert len(dispatcher_calls)==before
print("KCC_KIT_OPENAPI: PASS")
