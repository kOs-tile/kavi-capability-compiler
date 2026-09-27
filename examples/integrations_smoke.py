import asyncio
import kavi_capability_compiler as kcc

GET_SCHEMA={"type":"object","properties":{"id":{"type":"string"}},"required":["id"]}
UPDATE_SCHEMA={"type":"object","properties":{"id":{"type":"string"},"value":{"type":"string"}},"required":["id","value"]}

SOURCES={
    "generic":{
        "tools":[
            {"name":"get_record","description":"Get a record by ID","input_schema":GET_SCHEMA},
            {"name":"update_record","description":"Update a record","input_schema":UPDATE_SCHEMA},
        ]
    },
    "mcp":{
        "tools":[
            {"name":"get_record","description":"Get a record by ID","inputSchema":GET_SCHEMA},
            {"name":"update_record","description":"Update a record","inputSchema":UPDATE_SCHEMA},
        ]
    },
    "openai":{
        "tools":[
            {"type":"function","function":{"name":"get_record","description":"Get a record by ID","parameters":GET_SCHEMA}},
            {"type":"function","function":{"name":"update_record","description":"Update a record","parameters":UPDATE_SCHEMA}},
        ]
    },
    "anthropic":{
        "tools":[
            {"name":"get_record","description":"Get a record by ID","input_schema":GET_SCHEMA},
            {"name":"update_record","description":"Update a record","input_schema":UPDATE_SCHEMA},
        ]
    },
    "openapi":{
        "openapi":"3.1.0",
        "paths":{
            "/records/get":{"post":{
                "operationId":"get_record",
                "description":"Get a record by ID",
                "requestBody":{"content":{"application/json":{"schema":GET_SCHEMA}}},
            }},
            "/records/update":{"post":{
                "operationId":"update_record",
                "description":"Update a record",
                "requestBody":{"content":{"application/json":{"schema":UPDATE_SCHEMA}}},
            }},
        },
    },
}


async def exercise(source_format, payload):
    manifest=kcc.adapt_capabilities(source_format,payload,namespace="records")
    inventory=kcc.scan_manifest(manifest)
    ids={c["name"]:c["id"] for c in inventory["capabilities"]}
    capsule=kcc.compile_capsule(
        inventory,
        {"task":"Read one record","capabilities":[ids["get_record"]]},
        {"default":"allow"},
        now=100,
    )
    guard=kcc.Guard.from_capsule(capsule,inventory=inventory)
    dispatched=[]

    async def existing_agent_dispatcher(params):
        dispatched.append(dict(params))
        return {"id":params["id"],"value":"example"}

    result=await guard.dispatch(
        ids["get_record"],
        existing_agent_dispatcher,
        parameters={"id":"123"},
        now=101,
    )

    before=len(dispatched)
    try:
        await guard.dispatch(
            ids["update_record"],
            existing_agent_dispatcher,
            parameters={"id":"123","value":"blocked"},
            now=101,
        )
        raise AssertionError("outside-capsule capability executed")
    except kcc.AuthorityDenied:
        pass

    assert len(dispatched)==before
    assert result["executed"] is True
    return {
        "format":source_format,
        "manifest_digest":manifest["digest"],
        "inventory_digest":inventory["digest"],
        "grant":capsule["grants"][0]["id"],
    }


async def main():
    results=[]
    for source_format,payload in SOURCES.items():
        results.append(await exercise(source_format,payload))
    assert len({r["manifest_digest"] for r in results})==1
    assert len({r["inventory_digest"] for r in results})==1
    assert len({r["grant"] for r in results})==1
    print("KCC_INTEGRATION_RECIPES: PASS")
    for row in results:
        print(f"{row['format']}: {row['grant']}")


if __name__=="__main__":
    asyncio.run(main())
