# Roadmap

## M0 — Compiler kernel
**Status: shipped.**

Snapshot scan, audit, deterministic policy compilation, execution capsule, integrity/inventory/expiry verification, CLI, and CI.

## M1 — Evidence / Capability Benchmark
**Status: shipped.**

Evidence checkpoint:
- 487 sourced capabilities
- 30 MCP surfaces
- adversarial annotation cases
- effect + risk evidence model
- task-intent benchmark
- 99.49% mean authority reduction
- zero observed false-safe outcomes on the development corpus
- sealed post-freeze classification holdout
- inventory lock + drift benchmark
- bounded runtime authorization primitive

Exit report: `M1_EXIT.md`.

## M2 — Live Discovery + Authority Drift
**Status: shipped.**

Goal: move from snapshot-only evidence to authority observed from running MCP servers.

Scope:
- stdio `initialize -> tools/list`
- Streamable HTTP discovery
- common MCP config import without persisting secret values
- live inventory -> deterministic lock
- added / removed / changed authority detection
- bounded timeout and fail-closed protocol behavior
- compatibility against pinned published MCP servers
- fresh sealed discovery holdout

Exit gate:
- local stdio + Streamable HTTP integration tests pass
- real published MCP servers discover successfully without tool execution
- secret values do not enter KCC artifacts/errors
- live lock detects real or controlled live authority changes
- fresh sealed discovery holdout passes
- M1 safety gates remain green

## M3 — Hermes dogfood
**Status: next proving stage; not yet complete.**

M2 has exited. The framework-agnostic runtime guard prerequisite is now implemented and CI-backed. Remaining dogfood work:
- map a bounded Hermes capability surface into KCC IR
- discover/compile authority before a real workflow
- execute through the capsule guard
- prove an outside-capsule operation is blocked
- record one reproducible dogfood case study

Hermes is a proving ground, not a dependency of the core.

## M4 — Portable Enforcement SDK

After dogfood:
- harden the current Python guard into a versioned SDK surface
- generic adapter contract
- optional MCP proxy/bridge
- signed/verifiable capsules
- approval handoff contract

Compiler and runtime remain separable.

## M5 — Distribution / Product

- versioned package
- integration examples
- benchmark report
- landing page
- public v0.1
- dashboard/hosted control plane only if user demand justifies it
