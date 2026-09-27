# LangGraph ToolNode Validation

KCC validates placement immediately before a real LangGraph tool dispatcher using `langgraph==1.2.12`.

## Validation target

The case study uses:

- real LangChain `@tool` objects installed with LangGraph;
- real `langgraph.prebuilt.ToolNode`;
- real `ToolNode.invoke(...)` tool-call execution.

No model, LLM provider, API request, or credential is used.

When `ToolNode` is invoked directly outside a compiled graph, LangGraph requires a run-scoped `Runtime`; the case study supplies the public default `Runtime()` explicitly. Inside a compiled graph, LangGraph injects this runtime itself.

## Flow

```
real LangGraph/LangChain tool objects
        |
        | name + description + input schema
        v
KCC generic capability adapter
        |
        v
kcc.capabilities.v1
        |
        v
inventory + task intent + policy
        |
        v
kcc.capsule.v1
        |
        v
inventory-bound Guard
        |
        +--> allow -> real ToolNode.invoke(...)
        |
        +--> deny  -> ToolNode.invoke(...) is never called
```

This is deliberately a placement validation rather than a LangGraph-specific KCC adapter. KCC does not need to own the graph, state model, LLM node, or tools.

## Assertions

The CI case study proves:

1. real LangGraph/LangChain tool schemas normalize through KCC's existing generic contract;
2. a granted capability reaches a real `ToolNode` and its underlying tool exactly once;
3. an outside-capsule mutation is denied before `ToolNode.invoke()`;
4. a post-compile tool-set expansion causes inventory drift and fails closed;
5. LangGraph remains absent from KCC's installed core dependencies.

## Run locally

```bash
python -m pip install -e .
python -m pip install "langgraph==1.2.12"
python -m case_studies.langgraph_toolnode.run
```

The validation does not claim a full LLM-driven StateGraph loop. Its purpose is narrower and security-relevant: prove KCC can mediate the real tool-dispatch boundary without framework migration.
