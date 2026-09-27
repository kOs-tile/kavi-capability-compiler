from _shared import exercise_kit


TOOLS={
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
    result=exercise_kit("generic",TOOLS,namespace="custom-agent")
    print("KCC_INTEGRATION_KIT: generic-python: PASS")
    print(result)
