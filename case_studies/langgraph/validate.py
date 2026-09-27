from __future__ import annotations

import json
from importlib import metadata
from typing import Any

import kavi_capability_compiler as kcc
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime


LANGGRAPH_VERSION="1.2.12"
LANGCHAIN_CORE_VERSION="1.6.5"


def _tool_schema(tool: StructuredTool) -> dict[str, Any]:
    schema=tool.tool_call_schema
    if isinstance(schema,dict):
        return dict(schema)
    if hasattr(schema,"model_json_schema"):
        return schema.model_json_schema()
    return schema.schema()


calls={"get_record":0,"update_record":0}


def get_record(id: str) -> dict[str,str]:
    """Read one record."""
    calls["get_record"]+=1
    return {"id":id,"value":"example"}


def update_record(id: str, value: str) -> dict[str,Any]:
    """Update one record."""
    calls["update_record"]+=1
    return {"id":id,"value":value,"updated":True}


tools=[
    StructuredTool.from_function(
        get_record,
        name="get_record",
        description="Read one record by ID",
    ),
    StructuredTool.from_function(
        update_record,
        name="update_record",
        description="Update one record",
    ),
]

assert metadata.version("langgraph")==LANGGRAPH_VERSION
assert metadata.version("langchain-core")==LANGCHAIN_CORE_VERSION

source_tools=[
    {
        "name":tool.name,
        "description":tool.description,
        "input_schema":_tool_schema(tool),
    }
    for tool in tools
]

manifest=kcc.adapt_capabilities(
    "generic",
    {"tools":source_tools},
    namespace="langgraph-toolnode",
    source_metadata={
        "runtime":"langgraph",
        "langgraph_version":LANGGRAPH_VERSION,
        "langchain_core_version":LANGCHAIN_CORE_VERSION,
        "source":"BaseTool.tool_call_schema",
    },
)
inventory=kcc.scan_manifest(manifest)
ids={row["name"]:row["id"] for row in inventory["capabilities"]}

capsule=kcc.compile_capsule(
    inventory,
    {
        "task":"Read exactly one record without mutation",
        "capabilities":[ids["get_record"]],
        "capability_constraints":{
            ids["get_record"]:{
                "parameters":{
                    "id":{
                        "required":True,
                        "type":"string",
                        "pattern":"REC-[0-9]+",
                    }
                }
            }
        },
    },
    {"default":"allow"},
    now=100,
)
guard=kcc.Guard.from_capsule(capsule,inventory=inventory)
assert guard.inventory_bound


def kcc_tool_boundary(request,execute):
    tool_call=request.tool_call
    name=tool_call["name"]
    capability_id=ids.get(name)
    if capability_id is None:
        raise kcc.AuthorityDenied({
            "allowed":False,
            "reason":"capability_not_in_bound_inventory",
        })
    guard.require(
        capability_id,
        parameters=tool_call.get("args") or {},
        now=101,
    )
    return execute(request)


node=ToolNode(
    tools,
    handle_tool_errors=False,
    wrap_tool_call=kcc_tool_boundary,
)

read_result=node.invoke(
    [
        {
            "name":"get_record",
            "args":{"id":"REC-1"},
            "id":"read-1",
            "type":"tool_call",
        }
    ],
    runtime=Runtime(),
)
assert calls["get_record"]==1
assert calls["update_record"]==0
assert len(read_result)==1

denied_reason=None
try:
    node.invoke(
        [
            {
                "name":"update_record",
                "args":{"id":"REC-1","value":"should-not-run"},
                "id":"write-1",
                "type":"tool_call",
            }
        ],
        runtime=Runtime(),
    )
except kcc.AuthorityDenied as exc:
    denied_reason=exc.reason

assert denied_reason=="capability_not_granted"
assert calls["update_record"]==0

result={
    "validation":"kcc.langgraph-toolnode.v1",
    "langgraph_version":metadata.version("langgraph"),
    "langchain_core_version":metadata.version("langchain-core"),
    "source_schema":"BaseTool.tool_call_schema",
    "programmatic_runtime_supplied":True,
    "inventory_bound":guard.inventory_bound,
    "allowed_read_executed":calls["get_record"]==1,
    "denied_update_executed":calls["update_record"]>0,
    "denied_reason":denied_reason,
    "core_public_api_framework_neutral":not any(
        token in name.lower()
        for name in kcc.__all__
        for token in ("langgraph","langchain")
    ),
}
print(json.dumps(result,indent=2,sort_keys=True))
