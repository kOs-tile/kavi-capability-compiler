# M4 Exit Report — Embedded Enforcement SDK

M4 turns KCC into a library that developers embed into an existing agent stack.

## Product boundary

KCC does **not** require:

- a KCC daemon
- a desktop/local host
- a KAVI/Hermes/Codex runtime
- a hosted control plane
- a framework migration
- KCC-owned credentials, storage, or identity

The host application keeps its own model, tool registry, dispatcher, network, credentials, and deployment topology.

## Core install

Default install:

```bash
pip install kavi-capability-compiler
```

Core runtime dependencies: **0 required third-party packages**.

Optional extras:

- `[mcp]` — live MCP discovery
- `[signing]` — Ed25519 signed capsules
- `[all]` — development/integration convenience

CI installs the default package separately and verifies the public SDK plus core manifest CLI without optional integrations.

A built wheel is also installed into a fresh virtual environment with `--no-deps`; embedded SDK import and manifest/scan-manifest commands pass.

## Public SDK

Stable framework-neutral import surface includes:

- capability adapters / universal manifest
- manifest -> inventory normalization
- capsule compilation / verification
- inventory locks / drift
- `Guard`
- `AuthorityDenied`
- `ApprovalRequired`
- `CapabilityDenied`

Project-specific KAVI/Hermes/Codex operations are not part of the public API or CLI.

## Guard model

`Guard` runs immediately before the host application's own dispatcher.

Supported host styles:

- synchronous dispatcher
- asynchronous dispatcher

Denied calls do not reach the dispatcher.

Approval-required authority is surfaced as a distinct host-owned handoff rather than a KCC UI or approval service.

## Distributed trust

Signed capsules are optional.

The `[signing]` extra provides:

- Ed25519 key generation helpers
- exact-capsule signatures
- external `key_id -> trusted public key` binding
- envelope integrity
- capsule integrity
- expiry verification
- wrong-key / tamper / expiry fail-closed behavior

The signed envelope cannot make its own key trusted.

KCC does not provide key storage, KMS, identity, or secret management.

## Schemas

Published contracts:

- `kcc.capabilities.v1`
- `kcc.signed-capsule.v1`

## Recorded CI checkpoint

Final M4 branch:

- full suite: **79 passed**
- live discovery integration suite: **11 passed**
- minimal core install: PASS
- dependency-free wheel smoke: PASS
- framework equivalence: PASS
- M1 dangerous recall: **100%**
- M1 false-safe: **0**
- mean task authority reduction: **99.49%**
- drift recall: **100%**
- authorize p95: approximately **0.012 ms**
- compile p95: approximately **0.047 ms**

Latency figures are GitHub Actions microbenchmarks, not production throughput guarantees.

## M4 verdict

**PASS.**

KCC can now be embedded in another agent stack without requiring a KCC runtime service or local machine dependency.

The host can normalize its capability surface, compile bounded task authority, place a generic guard before its own dispatcher, distinguish approval handoff from denial, and optionally verify signed capsules across trust boundaries.

## Next

M5 should focus on distribution and adoption rather than adding framework coupling:

- versioned public package/release
- integration recipes for common agent stacks
- benchmark report
- public documentation/landing page
- optional proxy/bridge as an adapter only if users need out-of-process enforcement
