from __future__ import annotations

from typing import Any, Mapping

from .manifest import (
    from_anthropic_tools,
    from_generic,
    from_mcp_tools,
    from_openai_tools,
    from_openapi,
)

SUPPORTED_SOURCE_FORMATS=("generic","mcp","openai","anthropic","openapi")


def _tool_list(payload: Any) -> list[Mapping[str, Any]]:
    if isinstance(payload,list):
        return payload
    if isinstance(payload,Mapping):
        tools=payload.get("tools")
        if isinstance(tools,list):
            return tools
    raise ValueError("Expected a tool list or object containing a tools list")


def adapt_capabilities(
    source_format: str,
    payload: Any,
    *,
    namespace: str,
    source_metadata: Mapping[str, Any] | None = None,
    server: str | None = None,
) -> dict[str, Any]:
    """Normalize a supported external capability format into kcc.capabilities.v1.

    External integrations do not need to subclass KCC. They may either call
    this adapter or emit the universal manifest directly.
    """
    kind=str(source_format).strip().lower()
    if kind=="generic":
        return from_generic(_tool_list(payload),namespace=namespace,source_metadata=source_metadata)
    if kind=="mcp":
        return from_mcp_tools(_tool_list(payload),namespace=namespace,server=server)
    if kind=="openai":
        return from_openai_tools(_tool_list(payload),namespace=namespace)
    if kind=="anthropic":
        return from_anthropic_tools(_tool_list(payload),namespace=namespace)
    if kind=="openapi":
        if not isinstance(payload,Mapping):
            raise ValueError("OpenAPI source must be an object")
        return from_openapi(payload,namespace=namespace,source_metadata=source_metadata)
    raise ValueError(f"Unsupported capability source format: {source_format}")
