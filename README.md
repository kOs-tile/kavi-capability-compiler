# KAVI Capability Compiler

> **Status — Active flagship.** M0 is shipped and CI-backed; M1 is focused on benchmarking the least-authority thesis against heterogeneous real MCP capability surfaces.


KCC is a framework-agnostic **least-authority compiler for AI agents**.

```
scan -> audit -> compile -> execution capsule -> verify
```

Given an observed capability surface, explicit task intent, and deterministic policy, KCC compiles a bounded authority artifact for one execution.

## Why

Agent systems accumulate standing authority through MCP servers, tools, credentials, APIs, filesystem access, skills, and sub-agents. Runtime gates ask whether a particular call should execute. KCC focuses on the earlier question:

> Why did this execution have this capability in the first place?

## M0

The current kernel provides:

- MCP snapshot -> canonical capability inventory
- deterministic side-effect classification and audit
- task intent + policy -> execution capsule
- deny precedence and fail-closed unknown authority
- capability fingerprints
- capsule integrity, inventory binding, drift, and expiry verification
- CLI and automated tests

### Security invariant

**Unknown authority never becomes silent authority.**

A capability whose effect cannot be classified cannot be automatically granted by a broad allow policy.

## Quick start

Python 3.11+.

```bash
python -m pip install -e .
pytest -q

kcc scan tests/fixtures/mcp_snapshot.json -o inventory.json
kcc audit inventory.json -o audit.json
kcc compile inventory.json --intent examples/intent.json --policy examples/policy.json -o capsule.json
kcc verify capsule.json --inventory inventory.json
```

## Current boundary

M0 is a working compiler kernel, not a validated security product. It does **not** yet claim semantic proof of tool behavior, runtime enforcement, signed capsules, live MCP discovery, or production-grade classifier accuracy.

M1 is explicitly designed to test whether the product thesis survives real MCP data. See `docs/ROADMAP.md`.

Earlier KAVI capability experiments and the ideas retained or rejected here are documented in `docs/RESEARCH_LINEAGE.md`.
