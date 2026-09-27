from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import kavi_capability_compiler as kcc


def manifest_from_function_tools(
    tools: Iterable[Any],
    *,
    namespace: str,
) -> dict[str, Any]:
    """Normalize real OpenAI Agents SDK FunctionTool objects through KCC.

    The adapter intentionally uses only the FunctionTool public metadata surface
    required to describe authority. It does not depend on Agent, Runner, model
    execution, credentials, or OpenAI network access.
    """
    rows=[]
    seen=set()
    for tool in tools:
        name=str(getattr(tool,"name","") or "").strip()
        description=str(getattr(tool,"description","") or "")
        schema=getattr(tool,"params_json_schema",None)
        invoke=getattr(tool,"on_invoke_tool",None)
        if not name:
            raise ValueError("FunctionTool name is required")
        if name in seen:
            raise ValueError(f"Duplicate FunctionTool name: {name}")
        if not isinstance(schema,dict):
            raise ValueError(f"FunctionTool params_json_schema must be an object: {name}")
        if not callable(invoke):
            raise ValueError(f"FunctionTool on_invoke_tool must be callable: {name}")
        seen.add(name)
        rows.append({
            "type":"function",
            "function":{
                "name":name,
                "description":description,
                "parameters":schema,
            },
        })
    return kcc.adapt_capabilities(
        "openai",
        {"tools":rows},
        namespace=namespace,
    )
