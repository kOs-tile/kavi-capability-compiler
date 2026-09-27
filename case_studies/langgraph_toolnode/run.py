from __future__ import annotations

import json
from importlib import metadata

import kavi_capability_compiler as kcc
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime


get_invocations=[]
update_invocations=[]
delete_invocations=[]
toolnode_invocations=[]


@tool
def get_record(id: str) -> str:
    """Get one record by ID."""
    get_invocations.append(id)
    return f"record:{id}"


@tool
def update_record(id: str, value: str) -> str:
    """Update one record by ID."""
    update_invocations.append((id,value))
    return f"updated:{id}"


@tool
def delete_record(id: str) -> str:
    """Delete one record by ID."""
    delete_invocations.append(id)
    return f"deleted:{id}"


def inventory_for(tools):
    definitions=[]
    for item in tools:
        schema=item.get_input_schema().model_json_schema()
        assert item.name
        assert isinstance(item.description,str)
        assert isinstance(schema,dict)
        definitions.append({
            "name":item.name,
            "description":item.description,
            "input_schema":schema,
        })
    manifest=kcc.adapt_capabilities(
        "generic",
        {"tools":definitions},
        namespace="langgraph",
    )
    return manifest,kcc.scan_manifest(manifest)


def invoke_toolnode(node: ToolNode, tool_name: str, params: dict, call_id: str):
    toolnode_invocations.append(tool_name)
    result=node.invoke(
        [
            {
                "name":tool_name,
                "args":dict(params),
                "id":call_id,
                "type":"tool_call",
            }
        ],
        runtime=Runtime(),
    )
    messages=result["messages"] if isinstance(result,dict) else result
    assert messages
    return messages[-1].content


def main():
    tools=[get_record,update_record]
    node=ToolNode(tools)
    manifest,inventory=inventory_for(tools)
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
            "ttl_seconds":60,
        },
        {"default":"allow"},
        now=100,
    )
    guard=kcc.Guard.from_capsule(capsule,inventory=inventory)

    allowed=guard.dispatch_sync(
        ids["get_record"],
        lambda params: invoke_toolnode(node,"get_record",params,"call-read-1"),
        parameters={"id":"REC-1"},
        now=101,
    )
    assert allowed["executed"] is True
    assert allowed["result"]=="record:REC-1"
    assert get_invocations==["REC-1"]
    assert toolnode_invocations==["get_record"]

    before_node=len(toolnode_invocations)
    before_update=len(update_invocations)
    denied_reason=None
    try:
        guard.dispatch_sync(
            ids["update_record"],
            lambda params: invoke_toolnode(node,"update_record",params,"call-write-1"),
            parameters={"id":"REC-1","value":"blocked"},
            now=101,
        )
        raise AssertionError("outside-capsule ToolNode dispatch executed")
    except kcc.AuthorityDenied as exc:
        denied_reason=exc.reason
    assert denied_reason=="capability_not_granted"
    assert len(toolnode_invocations)==before_node
    assert len(update_invocations)==before_update

    _,expanded_inventory=inventory_for([get_record,update_record,delete_record])
    drift=kcc.Guard.from_capsule(
        capsule,
        inventory=expanded_inventory,
    ).authorize(
        ids["get_record"],
        parameters={"id":"REC-1"},
        now=101,
    )
    assert drift["allowed"] is False
    assert drift["reason"]=="inventory_drift"
    assert delete_invocations==[]

    result={
        "validation":"kcc.langgraph-toolnode.v1",
        "langgraph_version":metadata.version("langgraph"),
        "tool_count":len(tools),
        "manifest_version":manifest["schema_version"],
        "inventory_version":inventory["version"],
        "capsule_version":capsule["version"],
        "guard_inventory_bound":guard.inventory_bound,
        "allowed_toolnode_dispatches":len(toolnode_invocations),
        "allowed_tool_invocations":len(get_invocations),
        "denied_tool_invocations":len(update_invocations),
        "denied_reason":denied_reason,
        "expanded_surface_reason":drift["reason"],
        "model_or_api_call_performed":False,
        "pass":True,
    }
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
