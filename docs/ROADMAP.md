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
**Status: active.**

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

## M3 — KAVI/Hermes dogfood
**Status: active; M3A KAVI control-plane dogfood passed.**

M3A evidence:
- authoritative KAVI Dispatch Bridge contract adapted into KCC IR
- 5 standing capabilities -> 1 task-scoped grant
- 80% authority reduction for the read-only operator-snapshot task
- granted read allowed by runtime guard
- enqueue_task and approve_task blocked outside the capsule
- live production bridge health verified without extracting secrets

M3B:
- authenticated read-only live bridge discovery when the existing bearer is available through an authorized runtime
- Hermes-local adapter only after an actual Hermes capability/tool export or registry is available
- never invent a Hermes surface from chat history

Hermes/KAVI remain proving grounds, not dependencies of the core.

## M4 — Portable Enforcement SDK

After dogfood:
- Python guard
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
