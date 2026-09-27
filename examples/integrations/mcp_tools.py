from _shared import exercise_kit


MCP_TOOLS={
    "tools":[
        {
            "name":"get_record",
            "description":"Get a record by ID",
            "inputSchema":{
                "type":"object",
                "properties":{"id":{"type":"string"}},
                "required":["id"],
            },
        },
        {
            "name":"update_record",
            "description":"Update a record",
            "inputSchema":{
                "type":"object",
                "properties":{
                    "id":{"type":"string"},
                    "value":{"type":"string"},
                },
                "required":["id","value"],
            },
        },
    ]
}


if __name__=="__main__":
    result=exercise_kit(
        "mcp",
        MCP_TOOLS,
        namespace="records-mcp",
        server="records-server",
    )
    print("KCC_INTEGRATION_KIT: mcp-tools: PASS")
    print(result)
