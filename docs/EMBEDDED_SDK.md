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
kcc.inventory.v1
      |
      v
compile_capsule(...) -> kcc.capsule.v1
      |
      v
Guard
      |
      +--> allowed -> host dispatcher
      |
      +--> denied  -> never reaches dispatcher
```

## Minimal install

The v0.1.0 core package is available through KCC's live GitHub Pages Simple Repository:

```bash
python -m pip install --index-url https://kos-tile.github.io/kavi-capability-compiler/simple/ kavi-capability-compiler
```

You can also install the exact versioned GitHub Release wheel directly:

```bash
python -m pip install https://github.com/kOs-tile/kavi-capability-compiler/releases/download/v0.1.0/kavi_capability_compiler-0.1.0-py3-none-any.whl
```

The default package has no required runtime dependencies outside the Python standard library.

Optional integrations use the exact published wheel with PEP 508 extras metadata:

```bash
python -m pip install "kavi-capability-compiler[mcp] @ https://github.com/kOs-tile/kavi-capability-compiler/releases/download/v0.1.0/kavi_capability_compiler-0.1.0-py3-none-any.whl"
python -m pip install "kavi-capability-compiler[signing] @ https://github.com/kOs-tile/kavi-capability-compiler/releases/download/v0.1.0/kavi_capability_compiler-0.1.0-py3-none-any.whl"
python -m pip install "kavi-capability-compiler[all] @ https://github.com/kOs-tile/kavi-capability-compiler/releases/download/v0.1.0/kavi_capability_compiler-0.1.0-py3-none-any.whl"
```

The KCC Pages index intentionally contains KCC artifacts only. When an optional extra is installed from the direct wheel URL, pip resolves that extra's third-party dependencies from the normal package index.

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

guard = kcc.Guard.from_capsule(capsule, inventory=inventory)

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

Binding the Guard to the inventory used for compilation is the recommended runtime pattern. The binding makes the Guard fail closed if the capability surface is added to, removed from, or semantically changed before dispatch.

An unbound Guard remains available for trusted static registries, but it cannot independently detect post-compile registry drift.

An unsigned capsule is intended for a trusted in-process boundary. Its digest detects accidental or post-compile mutation; it does not authenticate an untrusted sender. If the capsule crosses a process, service, client, or network trust boundary, use the signed-capsule path or an equivalent host-authenticated transport.

See `SDK_COMPATIBILITY.md` for the frozen v0.1 contracts and exception semantics.

## Signed capsules

For distributed stacks where the compiler and executor are separate processes or services, install the optional signing extra from the exact published wheel:

```bash
python -m pip install "kavi-capability-compiler[signing] @ https://github.com/kOs-tile/kavi-capability-compiler/releases/download/v0.1.0/kavi_capability_compiler-0.1.0-py3-none-any.whl"
```

KCC signs the exact capsule with Ed25519.

Trust is external: the signed envelope contains a `key_id`, but the verifier must receive the trusted public key independently from the host environment. An envelope cannot declare itself trusted.

KCC does not provide key storage, KMS, identity, or secret management.

## Integration model

Existing runtimes can integrate in either direction:

1. **In-process** — call KCC directly as a library.
2. **Out-of-process within one trusted boundary** — emit `kcc.capabilities.v1`, compile elsewhere, and return the capsule over a host-authenticated channel.
3. **Distributed / separate trust boundary** — use `kcc.signed-capsule.v1` with independently configured trusted public keys.

Hermes, Codex, KAVI, LangGraph, custom agents, cloud runtimes, and local runtimes are all merely possible hosts. None is required by KCC.
