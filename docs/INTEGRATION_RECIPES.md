# Integration Recipes

KCC is designed to sit immediately before an existing agent stack's dispatcher.

The host keeps its own model, tool loop, credentials, storage, network, and deployment.

Common flow:

```python
manifest = kcc.adapt_capabilities(format, existing_tool_definitions, namespace="my-agent")
inventory = kcc.scan_manifest(manifest)
capsule = kcc.compile_capsule(inventory, task_intent, policy)
guard = kcc.Guard.from_capsule(capsule)

result = await guard.dispatch(
    capability_id,
    existing_dispatcher,
    parameters=tool_arguments,
)
```

## OpenAI function tools

If the host already has an OpenAI-style tools array:

```python
manifest = kcc.adapt_capabilities(
    "openai",
    {"tools": openai_tools},
    namespace="support-agent",
)
```

No OpenAI SDK dependency is required by KCC. The adapter reads the tool-definition shape only.

## Anthropic tools

```python
manifest = kcc.adapt_capabilities(
    "anthropic",
    {"tools": anthropic_tools},
    namespace="support-agent",
)
```

No Anthropic SDK dependency is required.

## MCP definitions

For already-known MCP tool metadata:

```python
manifest = kcc.adapt_capabilities(
    "mcp",
    {"tools": mcp_tools},
    namespace="filesystem",
)
```

This path does not require the optional MCP runtime extra.

If KCC itself must discover a running MCP server, install:

```bash
pip install "kavi-capability-compiler[mcp]"
```

## OpenAPI

```python
manifest = kcc.adapt_capabilities(
    "openapi",
    openapi_document,
    namespace="billing-api",
)
```

Operations with `operationId` become capabilities.

## Generic registries

For a custom agent stack, emit the smallest neutral shape:

```python
manifest = kcc.adapt_capabilities(
    "generic",
    {
        "tools": [
            {
                "name": "read_customer",
                "description": "Read one customer",
                "input_schema": {
                    "type": "object",
                    "properties": {"customer_id": {"type": "string"}},
                    "required": ["customer_id"],
                },
            }
        ]
    },
    namespace="crm-agent",
)
```

A custom integration may also emit `kcc.capabilities.v1` directly.

## Approval handoff

KCC does not own an approval UI.

If policy compiles a capability into the approval set:

```python
try:
    guard.require(capability_id, parameters=args)
except kcc.ApprovalRequired as request:
    send_to_your_existing_approval_system(request.decision)
```

That approval system may be a phone flow, WebAuthn, Slack, an internal UI, or another host-owned mechanism.

## Distributed compiler/executor

If compilation and execution happen across trust boundaries, install the signing extra and use signed capsules.

The executor must receive trusted public keys independently. A signed envelope cannot make its own signing key trusted.

## Executable reference

`examples/integrations_smoke.py` exercises generic JSON, MCP, OpenAI, Anthropic, and OpenAPI definitions through the same Guard boundary and is executed in CI.

## Executable integration kits

For complete runnable references, see `docs/INTEGRATION_KITS.md` and `examples/integration_kits/`.

The examples cover OpenAI function-tool definitions, Anthropic tools, MCP tool definitions, OpenAPI operations, and a custom Python registry. Every kit uses the same framework-neutral KCC contract and binds Guard to the current inventory.
