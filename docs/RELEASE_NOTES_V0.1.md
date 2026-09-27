# KAVI Capability Compiler v0.1.0

KCC v0.1 is the first public alpha of the framework-agnostic least-authority compiler and embedded enforcement SDK for AI agents.

## What it does

KCC takes an agent's available capability surface plus explicit task intent and policy, then compiles a smaller execution capsule containing only the authority needed for that task.

The host application keeps its own model, dispatcher, credentials, storage, identity, and deployment.

## v0.1 highlights

- zero-required-dependency embedded core
- universal `kcc.capabilities.v1` manifest
- adapters for generic JSON, MCP, OpenAI function tools, Anthropic tools, and OpenAPI
- deterministic capability fingerprints and inventory locks
- task-scoped execution capsules
- deny / approval / allow policy decisions
- operation and parameter constraints
- sync + async `Guard` before the host dispatcher
- optional Ed25519 signed capsules
- optional live MCP discovery
- framework-neutral execution evidence
- packaged public JSON schemas

## Evidence checkpoint

Recorded engineering benchmarks include:

- 487 sourced capabilities across 30 MCP surfaces
- 0 observed false-safe outcomes in the development corpus
- 100% dangerous recall at the recorded M1 checkpoint
- 63-capability sealed post-freeze holdout with 0 false-safe outcomes
- 99.49% mean task authority reduction across the 10-task benchmark
- framework-equivalent authority across five source formats
- denied calls do not reach the host dispatcher

See `docs/BENCHMARK_REPORT_V0.1.md` for limitations and exact interpretation.

## Install

```bash
pip install kavi-capability-compiler
```

Optional extras:

```bash
pip install "kavi-capability-compiler[mcp]"
pip install "kavi-capability-compiler[signing]"
```

## Important limits

v0.1 is alpha software.

KCC is not an identity provider, KMS, secret manager, hosted control plane, or proof that a tool is safe.

Its primary security invariant is:

> Unknown authority never becomes silent authority.
