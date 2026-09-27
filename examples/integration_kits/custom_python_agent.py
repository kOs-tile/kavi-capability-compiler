"""Custom Python agent registry -> KCC -> inventory-bound Guard.

The agent keeps its existing callable registry. KCC compiles authority from a neutral
description of that registry and mediates the final dispatch.
"""
import kavi_capability_compiler as kcc

def get_record(*,id):
    return {"id":id,"value":"example"}

def update_record(*,id,value):
    return {"id":id,"value":value}

registry={
    "get_record":get_record,
    "update_record":update_record,
}
definitions={
    "tools":[
        {
            "name":"get_record",
            "description":"Get a record by ID",
            "input_schema":{
                "type":"object",
                "properties":{"id":{"type":"string"}},
                "required":["id"],
            },
        },
        {
            "name":"update_record",
            "description":"Update a record",
            "input_schema":{
                "type":"object",
                "properties":{"id":{"type":"string"},"value":{"type":"string"}},
                "required":["id","value"],
            },
        },
    ]
}

manifest=kcc.adapt_capabilities("generic",definitions,namespace="custom-agent")
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

def host_dispatcher(capability_name,params):
    dispatcher_calls.append((capability_name,dict(params)))
    return registry[capability_name](**params)

result=guard.dispatch_sync(
    ids["get_record"],
    lambda params: host_dispatcher("get_record",params),
    parameters={"id":"REC-1"},
    now=101,
)
assert result["result"]=={"id":"REC-1","value":"example"}

before=len(dispatcher_calls)
try:
    guard.dispatch_sync(
        ids["update_record"],
        lambda params: host_dispatcher("update_record",params),
        parameters={"id":"REC-1","value":"blocked"},
        now=101,
    )
    raise AssertionError("outside-capsule mutation reached dispatcher")
except kcc.AuthorityDenied as exc:
    assert exc.reason=="capability_not_granted"

assert len(dispatcher_calls)==before
print("KCC_KIT_CUSTOM_PYTHON: PASS")
