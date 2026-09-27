# Integration Recipes

KCC is designed to sit immediately before an existing agent stack's dispatcher.

The host keeps its own model, tool loop, credentials, storage, network, and deployment. Framework names in this document describe capability-definition shapes or host environments; they are not KCC runtime dependencies.

The recommended flow is:

```python
manifest = kcc.adapt_capabilities(
    source_format,
    existing_tool_definitions,
    namespace="my-agent",
)
inventory = kcc.scan_manifest(manifest)
capsule = kcc.compile_capsule(inventory, task_intent, policy)
guard = kcc.Guard.from_capsule(capsule, inventory=inventory)

result = await guard.dispatch(
    capability_id,
    existing_dispatcher,
    parameters=tool_arguments,
)
```

Binding Guard to the current inventory is the recommended pattern because it rejects post-compile capability additions, removals, and semantic/schema drift before dispatch.

## Executable integration kits

Five credential-free kits run in CI and source distribution:

| Host/source shape | Reference kit |
| --- | --- |
| Generic Python/custom registry | `examples/integrations/generic_python.py` |
| OpenAI function tools | `examples/integrations/openai_tools.py` |
| Anthropic tools | `examples/integrations/anthropic_tools.py` |
| Raw MCP tool definitions | `examples/integrations/mcp_tools.py` |
| OpenAPI agent | `examples/integrations/openapi_agent.py` |

All five use the same shared runtime pattern in `examples/integrations/_shared.py`:

1. normalize source definitions to `kcc.capabilities.v1`;
2. scan to `kcc.inventory.v1`;
3. compile a read-only task capsule;
4. bind Guard to the inventory;
5. execute the granted read through the host dispatcher;
6. prove an outside-capsule update never reaches that dispatcher.

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
    server="filesystem-server",
)
```

This normalization path does not require the optional MCP runtime extra.

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

For a custom agent stack:

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

That approval system may be WebAuthn, a phone flow, Slack, an internal admin UI, or another host-owned mechanism.

## Distributed compiler/executor

If compilation and execution happen across trust boundaries, install the signing extra and use signed capsules.

The executor must receive trusted public keys independently. A signed envelope cannot make its own signing key trusted. Distributed replay prevention remains host state; see `ADVERSARIAL_SDK.md`.

## Existing equivalence reference

`examples/integrations_smoke.py` continues to express the same semantic capabilities in all five formats and proves cross-format authority equivalence in CI.
