# OpenAI Agents SDK Validation

KCC validates its framework-neutral integration boundary against the real OpenAI Agents SDK as a repository-only case study.

## Validation target

Pinned CI target:

```
openai-agents==0.22.3
```

The validation uses the SDK's public `FunctionTool` metadata and execution callback surface:

- `name`
- `description`
- `params_json_schema`
- `on_invoke_tool`

No model inference, Runner execution, hosted tool, OpenAI API request, or API key is used.

## Flow

```
real OpenAI Agents SDK FunctionTool objects
        |
        v
repo-only case-study adapter
        |
        v
existing KCC OpenAI capability adapter
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
        +--> allowed -> real FunctionTool.on_invoke_tool
        |
        +--> denied  -> SDK invocation callback is never called
```

The KCC core API and package metadata are unchanged. `openai-agents` is installed only inside a dedicated CI validation job.

## Assertions

The case study proves:

1. real FunctionTool metadata can be normalized without a framework-specific core adapter;
2. a task-scoped read capability executes through the SDK's real invocation callback;
3. an outside-capsule mutation is denied before `on_invoke_tool`;
4. adding a new tool after compilation causes inventory drift and fails closed;
5. the KCC core package retains zero required third-party runtime dependencies.

## Run locally

```bash
python -m pip install -e .
python -m pip install "openai-agents==0.22.3"
python -m case_studies.openai_agents.run
```

This validation is evidence for interoperability with one pinned SDK release, not a claim that all OpenAI Agents SDK tool categories or future releases are automatically compatible.
