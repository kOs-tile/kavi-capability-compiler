# KAVI Capability Compiler v0.1.0

KCC v0.1 is the first public alpha of the framework-agnostic least-authority compiler and embedded enforcement SDK for AI agents.

## What it does

KCC takes an agent's available capability surface plus explicit task intent and policy, then compiles a smaller execution capsule containing only the authority needed for that task.

The host application keeps its own model, dispatcher, credentials, storage, identity, and deployment.

## v0.1 highlights

- zero-required-dependency embedded core
- universal `kcc.capabilities.v1` manifest
- versioned `kcc.inventory.v1` and `kcc.inventory-lock.v1` authority inventory contracts
- versioned `kcc.capsule.v1` execution capsule contract
- adapters for generic JSON, MCP, OpenAI function tools, Anthropic tools, and OpenAPI
- deterministic capability fingerprints and inventory locks
- task-scoped execution capsules
- deny / approval / allow policy decisions
- operation and parameter constraints
- sync + async `Guard` before the host dispatcher
- optional Ed25519 signed capsules
- optional live MCP discovery
- framework-neutral execution evidence
- packaged public JSON schemas for manifests, inventories, inventory locks, capsules, and signed capsules
- explicit `kcc.sdk.v1` compatibility and exception semantics
- fail-closed rejection of unsupported/rehashed capsule versions and missing `fail_closed=true`
- inventory-bound Guard rejection of post-compile capability drift
- adversarial runtime tests for capsule tampering, approval bypass, stale inventory, and parameter-bound bypasses
- executable integration kits for Generic Python, OpenAI tool shapes, Anthropic tool shapes, MCP definitions, and OpenAPI
- pinned real-runtime validation at the tool-dispatch boundary for OpenAI Agents SDK 0.22.3, Anthropic Python SDK 1.8.0, and LangGraph 1.2.12
- CI release closure that checks raw wheel reproducibility, deterministic commit-epoch canonicalization of sdist archive metadata, bit-for-bit release-artifact equality, wheel surface, and Twine metadata
- pre-publication security hardening for canonical capability identity collisions and manifest/inventory/lock integrity
- remote MCP discovery requires HTTPS except for loopback development endpoints and rejects URL userinfo credentials
- immutable-SHA CI Actions, disabled checkout credential persistence, and vulnerability auditing of resolved optional dependencies
- clean CPython 3.11–3.14 compatibility gates for core, signing, and MCP extras plus clean sdist installation

## Evidence checkpoint

Recorded engineering benchmarks include:

- 487 sourced capabilities across 30 MCP surfaces
- 0 observed false-safe outcomes in the development corpus
- 100% dangerous recall at the recorded M1 checkpoint
- 63-capability sealed post-freeze holdout with 0 false-safe outcomes
- 99.49% mean task authority reduction across the 10-task benchmark
- framework-equivalent authority across five source formats
- denied calls do not reach the host dispatcher
- inventory-bound Guard rejects post-compile capability-surface drift
- real OpenAI Agents `FunctionTool.on_invoke_tool` allow/deny boundary validated without model/API calls
- real Anthropic `@beta_tool.call()` allow/deny boundary validated without model/API calls
- real LangGraph `ToolNode.invoke()` allow/deny boundary validated without an LLM

See `docs/BENCHMARK_REPORT_V0.1.md` for limitations and exact interpretation.

## Install

Until the PyPI mirror is available, install the exact v0.1.0 wheel from this GitHub Release:

```bash
python -m pip install https://github.com/kOs-tile/kavi-capability-compiler/releases/download/v0.1.0/kavi_capability_compiler-0.1.0-py3-none-any.whl
```

The release includes the wheel, source distribution, and `SHA256SUMS`. The live standards-compliant Simple Repository index exposes these same release assets through GitHub Pages without rebuilding them.

## Important limits

v0.1 is alpha software.

KCC is not an identity provider, KMS, secret manager, hosted control plane, or proof that a tool is safe.

Pinned runtime validations are interoperability evidence for the tested versions, not certification of every future framework release or every end-to-end agent loop.

Its primary security invariant is:

> Unknown authority never becomes silent authority.
