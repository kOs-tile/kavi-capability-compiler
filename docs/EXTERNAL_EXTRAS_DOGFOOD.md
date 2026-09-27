# External Optional-Extras Dogfood

This validation exercises the already-published v0.1.0 optional dependency groups exactly as an external consumer installs them from the GitHub Release wheel.

The cohort does not install repository source.

## Matrix

Six clean-install cells:

- CPython 3.11 + `signing`
- CPython 3.11 + `mcp`
- CPython 3.11 + `all`
- CPython 3.14 + `signing`
- CPython 3.14 + `mcp`
- CPython 3.14 + `all`

The two Python versions cover the lower and upper ends of KCC's declared support range. Full core compatibility across 3.11–3.14 is separately gated in CI and the external-consumer cohort.

## Installation

Each cell installs the exact v0.1.0 wheel with PEP 508 extras metadata, for example:

```bash
python -m pip install \
  "kavi-capability-compiler[signing] @ https://github.com/kOs-tile/kavi-capability-compiler/releases/download/v0.1.0/kavi_capability_compiler-0.1.0-py3-none-any.whl"
```

Third-party optional dependencies are resolved from their normal package indexes. KCC core remains zero-required-dependency.

## Signing checks

The `signing` and `all` cells verify:

- Ed25519 key generation
- exact capsule signing
- valid host-supplied trust key verification
- missing trust key rejection
- wrong key rejection
- tampered signed capsule rejection
- signed Guard authorization and dispatch
- signed Guard expiry failure

KCC does not persist or manage generated private keys.

## MCP checks

The `mcp` and `all` cells launch a local stdio MCP fixture and verify:

- MCP initialization and tools/list
- two discovered tools
- read classification for lookup
- delete classification for destructive mutation
- deterministic inventory lock
- injected environment secret is absent from discovery and lock artifacts
- missing server executable fails closed

No discovered tool is executed by the dogfood harness.

## Limits

This is public-package interoperability evidence, not a security certification.

The MCP probe is local stdio only; authenticated/remote HTTP security boundaries remain covered by the dedicated discovery regression suite. Signing keys are ephemeral test keys and do not represent production key-management practice.

No model calls, paid APIs, vendor credentials, or new required core dependencies are used.
