# M1 Exit Report

M1 answers one question: can KAVI Capability Compiler reduce standing agent authority into bounded task-scoped authority while failing closed on uncertain or dangerous capability semantics?

## Development corpus

- 487 sourced capabilities
- 30 distinct MCP surfaces
- 173 dangerous samples
- accuracy: 89.73%
- dangerous recall: 100%
- false-safe: 0
- unknown rate: 11.91%
- overblocking rate: 3.50%

## Sealed post-freeze holdout

The first holdout was labeled and committed before evaluation.

- 63 unseen capabilities
- 2 new surfaces
- 27 dangerous samples
- accuracy: 80.95%
- dangerous recall: 100%
- false-safe: 0
- unknown rate: 23.81%
- overblocking: 0%

After its first reveal this holdout becomes a regression set, not a future blind benchmark.

## Task-scoped authority

Across the 10-task benchmark:
- mean authority reduction: 99.49%
- average required capability count remains a small fraction of the 487-capability standing surface
- 4,845 unnecessary standing-authority exposures are removed across the benchmark task set

## Drift and performance

- synthetic real-corpus drift events detected: 100%
- authorization p95: approximately 0.017 ms at the recorded checkpoint
- compile p95: approximately 0.068 ms at the recorded checkpoint

These latency figures are local GitHub Actions microbenchmarks, not production throughput claims.

## Enforcement delivered in M1

- deterministic capability inventory
- audit evidence
- task + policy compilation
- execution capsules
- operation constraints
- parameter constraints
- schema-aware parameter validation
- fail-closed missing/invalid parameter behavior
- runtime call authorization primitive
- capsule integrity and expiry verification
- inventory lock and drift diff
- CLI surfaces for scan/audit/compile/verify/lock/diff/authorize

## M1 verdict

The original product thesis survives M1.

The strongest evidence is not generic classifier accuracy. It is the combination of:
1. zero observed false-safe outcomes in both development and first sealed holdout data;
2. 100% dangerous-capability recall at both checkpoints;
3. large task-scoped authority reduction;
4. explicit fail-closed treatment of uncertainty;
5. deterministic drift and runtime-bound enforcement primitives.

The main unresolved weakness is unknown-rate generalization on unseen surfaces. That should remain visible rather than being hidden by aggressive auto-classification.

## M2 boundary

M2 is **live discovery + real authority drift**, not a dashboard or hosted control plane.

Next:
1. live MCP `tools/list` discovery adapter;
2. stdio transport;
3. Streamable HTTP transport;
4. safe config import without secret capture;
5. inventory lock generation from live surfaces;
6. real add/remove/change drift tests;
7. fresh sealed holdout before any broader release claim.

Hermes dogfood follows live discovery; it does not replace it.
