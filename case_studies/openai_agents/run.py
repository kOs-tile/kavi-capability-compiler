from __future__ import annotations

import asyncio
import json

import kavi_capability_compiler as kcc
from agents import FunctionTool, __version__ as agents_version, function_tool, set_tracing_disabled
from agents.tool_context import ToolContext

from case_studies.openai_agents.adapter import manifest_from_function_tools


set_tracing_disabled(True)

get_invocations=[]
update_invocations=[]
delete_invocations=[]


@function_tool
def get_record(id: str) -> str:
    """Get one record by ID."""
    get_invocations.append(id)
    return f"record:{id}"


@function_tool
def update_record(id: str, value: str) -> str:
    """Update one record by ID."""
    update_invocations.append((id,value))
    return f"updated:{id}"


@function_tool
def delete_record(id: str) -> str:
    """Delete one record by ID."""
    delete_invocations.append(id)
    return f"deleted:{id}"


def inventory_for(tools):
    manifest=manifest_from_function_tools(tools,namespace="openai-agents")
    return manifest,kcc.scan_manifest(manifest)


async def invoke_sdk_tool(tool: FunctionTool, params: dict, call_id: str):
    arguments=json.dumps(params,separators=(",",":"))
    context=ToolContext(
        context=None,
        tool_name=tool.name,
        tool_call_id=call_id,
        tool_arguments=arguments,
    )
    return await tool.on_invoke_tool(context,arguments)


async def main():
    tools=[get_record,update_record]
    assert all(isinstance(tool,FunctionTool) for tool in tools)

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

    allowed=await guard.dispatch(
        ids["get_record"],
        lambda params: invoke_sdk_tool(get_record,params,"call-read-1"),
        parameters={"id":"REC-1"},
        now=101,
    )
    assert allowed["executed"] is True
    assert get_invocations==["REC-1"]

    before=len(update_invocations)
    denied_reason=None
    try:
        await guard.dispatch(
            ids["update_record"],
            lambda params: invoke_sdk_tool(update_record,params,"call-write-1"),
            parameters={"id":"REC-1","value":"blocked"},
            now=101,
        )
        raise AssertionError("outside-capsule FunctionTool invocation executed")
    except kcc.AuthorityDenied as exc:
        denied_reason=exc.reason
    assert denied_reason=="capability_not_granted"
    assert len(update_invocations)==before

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
        "validation":"kcc.openai-agents.v1",
        "openai_agents_version":agents_version,
        "function_tool_count":len(tools),
        "manifest_version":manifest["schema_version"],
        "inventory_version":inventory["version"],
        "capsule_version":capsule["version"],
        "guard_inventory_bound":guard.inventory_bound,
        "allowed_sdk_invocations":len(get_invocations),
        "denied_sdk_invocations":len(update_invocations),
        "denied_reason":denied_reason,
        "expanded_surface_reason":drift["reason"],
        "model_or_api_call_performed":False,
        "pass":True,
    }
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    asyncio.run(main())
