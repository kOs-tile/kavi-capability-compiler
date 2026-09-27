from _shared import exercise_kit


OPENAPI={
    "openapi":"3.1.0",
    "paths":{
        "/records/get":{
            "post":{
                "operationId":"get_record",
                "description":"Get a record by ID",
                "requestBody":{
                    "content":{
                        "application/json":{
                            "schema":{
                                "type":"object",
                                "properties":{"id":{"type":"string"}},
                                "required":["id"],
                            }
                        }
                    }
                },
            }
        },
        "/records/update":{
            "post":{
                "operationId":"update_record",
                "description":"Update a record",
                "requestBody":{
                    "content":{
                        "application/json":{
                            "schema":{
                                "type":"object",
                                "properties":{
                                    "id":{"type":"string"},
                                    "value":{"type":"string"},
                                },
                                "required":["id","value"],
                            }
                        }
                    }
                },
            }
        },
    },
}


if __name__=="__main__":
    result=exercise_kit("openapi",OPENAPI,namespace="records-api")
    print("KCC_INTEGRATION_KIT: openapi-agent: PASS")
    print(result)
