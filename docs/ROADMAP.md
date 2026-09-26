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

Delivered:
- stdio `initialize -> tools/list`
- Streamable HTTP discovery
- secret-safe MCP config import
- live inventory -> deterministic lock
- added / removed / changed authority detection
- bounded timeout and fail-closed protocol behavior
- compatibility against pinned published MCP servers
- sealed discovery holdout

## M3 — Framework-Agnostic Integration & Enforcement
**Status: active.**

Goal: make KCC usable by existing agent/tool stacks without requiring framework migration or modifications to the agent runtime.

Core contract:
`external capability definitions -> kcc.capabilities.v1 -> KCC inventory -> task capsule -> generic runtime guard`

Required source adapters:
- MCP tool definitions
- OpenAI function tools
- Anthropic tools
- OpenAPI operations
- generic JSON capability registries

Exit gates:
- equivalent authority expressed in different source formats normalizes to the same semantic manifest
- equivalent manifests produce the same KCC inventory and task-scoped grants
- provenance/source-format changes alone do not create authority drift
- schema/authority changes do create deterministic drift
- same-named capabilities in different namespaces do not collide
- denied calls never reach the caller-supplied dispatcher
- all M1/M2 safety gates remain green

Existing KAVI control-plane dogfood is retained as a case study only. KAVI, Hermes, Codex, LangGraph, or any other runtime may be used later as validation targets; none is a dependency or milestone prerequisite.

## M4 — Portable Enforcement SDK

After M3:
- stabilize the generic adapter + manifest API
- harden the Python runtime guard into a versioned SDK
- optional MCP proxy/bridge
- signed/verifiable capsules
- approval handoff contract
- integration kits for common runtimes

Compiler and runtime remain separable.

## M5 — Distribution / Product

- versioned package
- integration examples
- benchmark report
- landing page
- public v0.1
- dashboard/hosted control plane only if user demand justifies it
