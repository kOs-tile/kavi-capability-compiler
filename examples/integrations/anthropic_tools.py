from _shared import exercise_kit


ANTHROPIC_TOOLS={
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
    result=exercise_kit("anthropic",ANTHROPIC_TOOLS,namespace="anthropic-shaped-agent")
    print("KCC_INTEGRATION_KIT: anthropic-tools: PASS")
    print(result)
