from _shared import exercise_kit


OPENAI_TOOLS={
    "tools":[
        {
            "type":"function",
            "function":{
                "name":"get_record",
                "description":"Get a record by ID",
                "parameters":{
                    "type":"object",
                    "properties":{"id":{"type":"string"}},
                    "required":["id"],
                },
            },
        },
        {
            "type":"function",
            "function":{
                "name":"update_record",
                "description":"Update a record",
                "parameters":{
                    "type":"object",
                    "properties":{
                        "id":{"type":"string"},
                        "value":{"type":"string"},
                    },
                    "required":["id","value"],
                },
            },
        },
    ]
}


if __name__=="__main__":
    result=exercise_kit("openai",OPENAI_TOOLS,namespace="openai-shaped-agent")
    print("KCC_INTEGRATION_KIT: openai-tools: PASS")
    print(result)
