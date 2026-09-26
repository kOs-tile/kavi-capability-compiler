# M1 Capability Benchmark

This benchmark exists to falsify the product thesis, not market it.

## Question

Can KAVI Capability Compiler reduce standing authority per task without turning dangerous capabilities into ordinary safe/read authority?

KCC is **not** trying to replace server-level read-only modes, IAM, OAuth scopes, or runtime policy engines. Those remain useful upstream/downstream controls. The compiler's job is to derive the smallest task-scoped capability set from the authority that is actually available.

## Ground truth contract

Every corpus row must include:

- `server`
- exact `name`
- source description
- `expected_effect`
- `dangerous`
- public `source` provenance
- MCP annotations when the source publishes them

Declared annotations are evidence, not proof. Missing annotations must never imply safety.

## Safety metrics

Primary metric:

**False-safe rate** = dangerous capabilities classified as ordinary `read`.

Also report:

- classification accuracy
- unknown rate
- confusion matrix
- per-server results
- dangerous sample count

Unknown is intentionally preferable to false-safe because the compiler can fail closed.

## Dataset stages

- Seed: sourced capabilities from heterogeneous public MCP servers.
- M1a: 100+ real capabilities.
- M1b: 300–500 capabilities across 30+ MCP surfaces.
- Adversarial: misleading names/descriptions, missing annotations, schema drift, mixed read/write tools.

## Product benchmark

Classification is only one component. The product gate must also measure:

- discovery recall
- dangerous-capability recall
- authority reduction per task
- approval burden
- drift detection
- compile latency
- task success under compiled authority

Comparators:

1. standing/static permissions
2. per-call probabilistic gate
3. KCC precompiled authority
4. KCC + optional probabilistic gate

The benchmark should publish failures and ambiguous cases, not just aggregate scores.
