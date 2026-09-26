# Embedded SDK

KCC is designed to be embedded inside an existing agent stack.

It is **not** a desktop application, local daemon, hosted dependency, or framework migration requirement.

The host application keeps control of:

- its model/runtime
- its tool registry
- its dispatcher
- its credentials
- its network topology
- its storage
- its identity system

KCC contributes one narrow authority boundary:

```
existing agent stack
      |
      v
capability definitions
      |
      v
kcc.capabilities.v1
      |
      v
compile_capsule(...)
      |
      v
Guard
      |
      +--> allowed -> host dispatcher
      |
      +--> denied  -> never reaches dispatcher
```

## Minimal install

```bash
pip install kavi-capability-compiler
```

The default package has no required runtime dependencies outside the Python standard library.

Optional integrations:

```bash
pip install "kavi-capability-compiler[mcp]"
pip install "kavi-capability-compiler[signing]"
pip install "kavi-capability-compiler[all]"
```

MCP discovery is optional. Signed capsules are optional. Neither is required to embed the core compiler and guard.

## Host-stack example

```python
import kavi_capability_compiler as kcc

manifest = kcc.adapt_capabilities(
    "generic",
    {
        "tools": [
            {
                "name": "read_customer",
                "description": "Read a customer record",
                "input_schema": {
                    "type": "object",
                    "properties": {"customer_id": {"type": "string"}},
                    "required": ["customer_id"],
                },
            },
            {
                "name": "delete_customer",
                "description": "Delete a customer record",
                "input_schema": {
                    "type": "object",
                    "properties": {"customer_id": {"type": "string"}},
                    "required": ["customer_id"],
                },
            },
        ]
    },
    namespace="crm",
)

inventory = kcc.scan_manifest(manifest)
ids = {c["name"]: c["id"] for c in inventory["capabilities"]}

capsule = kcc.compile_capsule(
    inventory,
    {
        "task": "Read one customer",
        "capabilities": [ids["read_customer"]],
    },
    {"default": "allow"},
)

guard = kcc.Guard.from_capsule(capsule)

async def my_existing_dispatcher(params):
    return await crm.read_customer(**params)

result = await guard.dispatch(
    ids["read_customer"],
    my_existing_dispatcher,
    parameters={"customer_id": "123"},
)
```

No KCC server is required. The dispatcher remains the application's own function.

A capability outside the capsule is rejected before the dispatcher is called.

## Signed capsules

For distributed stacks where the compiler and executor are separate processes or services, install the optional signing extra:

```bash
pip install "kavi-capability-compiler[signing]"
```

KCC signs the exact capsule with Ed25519.

Trust is external: the signed envelope contains a `key_id`, but the verifier must receive the trusted public key independently from the host environment. An envelope cannot declare itself trusted.

KCC does not provide key storage, KMS, identity, or secret management.

## Integration model

Existing runtimes can integrate in either direction:

1. **In-process** — call KCC directly as a library.
2. **Out-of-process** — emit `kcc.capabilities.v1`, compile elsewhere, return a capsule to the runtime.
3. **Distributed** — use a signed capsule between compiler and executor.

Hermes, Codex, KAVI, LangGraph, custom agents, cloud runtimes, and local runtimes are all merely possible hosts. None is required by KCC.
