# KAVI Capability Compiler

> **Status — Active flagship.** M0 and M1 are shipped and CI-backed. M2 is validating live MCP discovery, secret-safe config import, lockfiles, and real authority drift.

KCC is a framework-agnostic **least-authority compiler for AI agents**.

```
discover/scan -> audit -> compile -> execution capsule -> verify/authorize
```

Given an observed capability surface, explicit task intent, and deterministic policy, KCC compiles a bounded authority artifact for one execution.

## Why

Agent systems accumulate standing authority through MCP servers, tools, credentials, APIs, filesystem access, skills, and sub-agents. Runtime gates ask whether a particular call should execute. KCC focuses on the earlier question:

> Why did this execution have this capability in the first place?

## What is shipped

### Compiler kernel
- MCP snapshot -> canonical capability inventory
- deterministic effect + risk evidence analysis
- task intent + policy -> execution capsule
- deny precedence and fail-closed unknown authority
- operation and parameter constraints
- capability fingerprints and capsule integrity
- runtime `authorize_call` primitive
- inventory locks and drift diff

### M1 evidence
- 487 sourced capabilities across 30 MCP surfaces
- 173 dangerous samples
- 0 observed false-safe outcomes
- 100% dangerous-capability recall on the development corpus
- 99.49% mean authority reduction across the 10-task benchmark
- first sealed classification holdout: 63 unseen capabilities, 0 false-safe

These are benchmark checkpoint measurements, not production security guarantees. See `docs/M1_EXIT.md`.

### M2 live discovery
- official MCP Python SDK stdio discovery
- Streamable HTTP discovery
- config-driven discovery
- secret-safe config summaries
- live discovery -> deterministic inventory lock
- live added/removed/changed authority detection
- bounded discovery timeouts
- published official MCP compatibility validation

## Security invariant

**Unknown authority never becomes silent authority.**

Uncertain authority fails closed into denial/approval behavior rather than becoming an automatic grant.

## Quick start

Python 3.11+.

```bash
python -m pip install -e .
pytest -q

# Static snapshot
kcc scan tests/fixtures/mcp_snapshot.json -o inventory.json
kcc audit inventory.json -o audit.json
kcc compile inventory.json --intent examples/intent.json --policy examples/policy.json -o capsule.json
kcc verify capsule.json --inventory inventory.json

# Live MCP discovery
kcc discover-stdio python tests/fixtures/live_mcp_server.py \
  -o discovery.json --lock-output inventory.lock.json

kcc config-summary mcp.json -o mcp.safe.json
kcc discover-config mcp.json my-server \
  -o discovery.json --lock-output inventory.lock.json
```

## Current boundary

KCC is not a hosted gateway, IAM replacement, secret manager, or autonomous remediation system. Live discovery does not automatically execute discovered tools. Runtime enforcement is intentionally a small portable primitive.

M2 must finish with reproducible live discovery/drift evidence before Hermes becomes the dogfood target.

See `docs/ROADMAP.md`, `docs/M2_LIVE_DISCOVERY.md`, and `docs/M2_COMPATIBILITY.md`.

## KAVI ecosystem

KCC stays independent of the surrounding research stack. Integration responsibilities and non-goals are documented in `docs/ECOSYSTEM.md`.
