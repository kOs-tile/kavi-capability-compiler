# LangGraph ToolNode Validation

This is an independent validation target, not a KCC core integration.

Pinned validation environment:

- `langgraph==1.2.12`
- `langchain-core==1.6.5`
- no model provider
- no API key
- no hosted service

## Boundary under test

The case study creates real LangChain `StructuredTool` objects, reads their actual `BaseTool.tool_call_schema`, and normalizes that metadata through KCC's existing generic contract.

It then uses LangGraph's real `ToolNode.wrap_tool_call` interception point:

```
ToolNode receives tool call
        |
        v
KCC Guard.require(...)
        |
        +-- allow --> LangGraph execute(request) --> BaseTool
        |
        +-- deny  --> execute(request) is never called
```

The KCC package contains no LangGraph/LangChain dependency or framework-specific public API.

## Run

From a repository checkout with the case-study dependencies installed:

```bash
python case_studies/langgraph/validate.py
```

CI installs the pinned third-party versions only for this validation job.

LangGraph 1.2.12 currently requires an explicit `Runtime()` when `ToolNode` is invoked programmatically outside a compiled graph, so the validation supplies that host runtime object explicitly.

The validation passes only if the allowed read reaches the real tool and the denied update never reaches its underlying function.
