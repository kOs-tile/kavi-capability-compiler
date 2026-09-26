# Roadmap

## M0 — compiler kernel
Status: shipped.

## M1 — Capability Benchmark v0.1
Prove the wedge before expanding product scope.

Dataset target:
- 30 heterogeneous MCP servers/snapshots
- 300–500 tools
- hand-labeled side-effect/effective-authority ground truth
- adversarial descriptions/schemas
- capability drift scenarios
- task-intent corpus

Metrics:
- discovery recall
- side-effect precision/recall
- dangerous-capability recall
- false-safe rate (primary safety metric)
- unknown rate
- authority reduction per task
- drift detection recall
- compile latency
- approval burden

Comparators:
1. static standing permissions
2. per-call probabilistic gate (Jev-style)
3. KCC precompiled authority
4. KCC + probabilistic ambiguous-call gate

Exit gate: demonstrate reproducible authority reduction without unacceptable false-safe behavior.

## M2 — Hermes dogfood
Only after M1 passes: map Hermes capabilities into KCC IR, compile before a bounded workflow, and prove an unauthorized call is blocked.
