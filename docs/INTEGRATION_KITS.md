# Integration Kits

KCC integrates at the authority boundary immediately before an existing host dispatcher. The host keeps its model loop, SDKs, credentials, transport, storage, and deployment.

The repository contains five executable, dependency-free reference kits:

| Host capability shape | Example |
| --- | --- |
| OpenAI function tools | `examples/integration_kits/openai_tools.py` |
| Anthropic tools | `examples/integration_kits/anthropic_tools.py` |
| MCP tool definitions | `examples/integration_kits/mcp_tools.py` |
| OpenAPI operations | `examples/integration_kits/openapi_agent.py` |
| Custom Python registry | `examples/integration_kits/custom_python_agent.py` |

These examples intentionally do **not** import OpenAI, Anthropic, MCP, LangGraph, or another agent framework. They consume only the framework's capability-definition shape.

## Canonical embedded pattern

```python
manifest = kcc.adapt_capabilities(source_format, definitions, namespace="my-agent")
inventory = kcc.scan_manifest(manifest)
capsule = kcc.compile_capsule(inventory, task_intent, policy)

guard = kcc.Guard.from_capsule(capsule, inventory=inventory)

result = await guard.dispatch(
    capability_id,
    existing_dispatcher,
    parameters=tool_arguments,
)
```

Binding the current inventory is recommended. If the capability surface changes after compilation, Guard fails closed with inventory drift rather than silently executing against a stale authority contract.

## Placement

The protected path should be:

```
agent/model loop
      |
      v
tool selection
      |
      v
KCC Guard
      |
      +---- allow ----> existing host dispatcher
      |
      +---- deny -----> dispatcher is not called
      |
      +---- approval -> host-owned approval workflow
```

A direct code path that calls the host dispatcher without Guard is outside KCC's mediation boundary. Hosts should centralize protected dispatch through this boundary.

## Approval

KCC does not create an approval UI.

```python
try:
    guard.require(capability_id, parameters=args)
except kcc.ApprovalRequired as request:
    send_to_existing_approval_workflow(request.decision)
```

Approval may be implemented by the host with WebAuthn, phone approval, Slack, an admin UI, or another workflow.

## Distributed compiler/executor

Unsigned capsules are intended for a trusted in-process or equivalently authenticated boundary. If compiler and executor cross a trust boundary, use `kcc.signed-capsule.v1` or an equivalent host-authenticated transport and configure trusted public keys independently.

KCC deliberately does not provide KMS, key storage, identity, a replay database, or a hosted gateway.

## Run all kits

```bash
python examples/integration_kits/run_all.py
```

CI executes the kits and verifies that the core package still has zero required third-party runtime dependencies.
