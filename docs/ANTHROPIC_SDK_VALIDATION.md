# Anthropic Python SDK Validation

KCC validates its framework-neutral authority boundary against real Anthropic Python SDK beta-tool objects as a repository-only case study.

## Validation target

Pinned CI target:

```
anthropic==1.8.0
```

The validation creates tools with the SDK's real `@beta_tool` decorator. The SDK derives JSON Schema from function signatures/docstrings; each tool exposes `to_dict()` for API-compatible metadata and `.call()` for local execution.

No Anthropic client, Claude inference, HTTP request, API key, or networked tool-runner loop is used.

## Flow

```
real Anthropic @beta_tool objects
        |
        | tool.to_dict()
        v
existing KCC Anthropic adapter
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
        +--> allow -> real SDK tool.call(...)
        |
        +--> deny  -> tool.call(...) is never reached
```

## Assertions

The case study proves:

1. real SDK-derived tool schemas normalize through the existing generic KCC contract;
2. a granted tool executes through the SDK object's real `.call()` method;
3. an outside-capsule mutation is denied before the SDK callback;
4. adding another beta tool after compilation creates inventory drift and fails closed;
5. the KCC core package remains dependency-free.

It does **not** claim that Anthropic's networked `client.beta.messages.tool_runner(...)` loop is validated, because that loop requires model/API interaction. That can be tested later as an explicitly authorized live validation.

## Run locally

```bash
python -m pip install -e .
python -m pip install "anthropic==1.8.0"
python -m case_studies.anthropic_sdk.run
```
