# External Runtime Validation — v0.1

KCC v0.1 keeps framework-specific runtime code outside the installed core package. The following pinned SDK/runtime validations are repository-only evidence that the same framework-neutral KCC contracts can mediate real tool-execution boundaries.

| Runtime | Pinned version | Real boundary exercised | Result |
| --- | ---: | --- | --- |
| OpenAI Agents SDK | 0.22.3 | `FunctionTool.params_json_schema` + real `on_invoke_tool` callback | allow executes once; denied mutation executes zero times; expanded surface fails as `inventory_drift` |
| Anthropic Python SDK | 1.8.0 | real `@beta_tool.to_dict()` + real `.call()` | allow executes once; denied mutation executes zero times; expanded surface fails as `inventory_drift` |
| LangGraph | 1.2.12 | real LangChain tools + real `ToolNode.invoke()` | allow reaches ToolNode/tool once; denied mutation never reaches ToolNode; expanded surface fails as `inventory_drift` |

All three validations also assert that the installed KCC core still has zero required third-party runtime dependencies.

## What these validations establish

They show that KCC can be placed immediately before real framework tool-dispatch boundaries without changing the KCC core architecture or requiring framework migration.

The repeated pattern is:

```
real framework tool surface
        |
        v
existing KCC source adapter / neutral manifest
        |
        v
kcc.capabilities.v1
        |
        v
kcc.inventory.v1
        |
        v
kcc.capsule.v1
        |
        v
inventory-bound Guard
        |
        +--> allow -> framework's real tool executor
        |
        +--> deny  -> framework executor is not called
```

## Deliberate limits

These are pinned-version interoperability validations, not universal framework certification.

They do not claim:

- compatibility with every future SDK/runtime release;
- safety of the underlying tool implementation;
- complete mediation if a host exposes an alternate direct-dispatch path around Guard;
- end-to-end model-loop validation for every framework;
- networked Anthropic `tool_runner` validation;
- identity, replay-store, KMS, sandbox, or secret-management guarantees.

The OpenAI Agents and Anthropic cases deliberately perform no model/API request. The LangGraph case exercises the real ToolNode dispatcher without an LLM.

Framework-specific dependencies remain CI/case-study dependencies only and are not part of `kavi-capability-compiler` core metadata.
