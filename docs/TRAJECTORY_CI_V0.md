# Trajectory CI Gate — experimental v0

KCC's embedded Guard enforces **authority before dispatch**. This optional CI tool
answers a separate, observational question: **did a host-recorded execution
follow a declared tool-call DAG?** It does not alter KCC's capsules, SDK,
dispatchers, or published v0.1.1 behavior.

## Run

```bash
python scripts/trajectory_ci.py --policy examples/trajectory/policy.json --trace examples/trajectory/pass.json
# exit 0 / pass
python scripts/trajectory_ci.py --policy examples/trajectory/policy.json --trace examples/trajectory/fail.json
# exit 1 / trajectory violation (approval bypass)
python -m pytest -q tests/test_trajectory_ci.py
```

The workflow `.github/workflows/trajectory-ci.yml` runs **synthetic regression
fixtures only**. It does not yet process live agent traces. A future trusted
host or CI producer must generate an immutable trace for a real execution,
then run the evaluator against the expected DAG. Do not mark this as
production enforcement or a real-runtime CI gate before that integration.

## Contracts

- Policy version `kcc.trajectory-policy.v0`: `nodes`, each with `id`,
  `kind`, `capability_id`, `operation`, and `after` prerequisite node IDs.
- Trace version `kcc.trajectory-trace.v0`: ordered `events`, each with
  `node_id`, `kind`, `capability_id`, `operation`, `outcome`.
- Event kinds: `dispatch`, `approval`, `denial`; required outcomes:
  `executed`, `approved`, `denied` respectively.
- Every golden node must appear exactly once. Independent DAG nodes can
  commute. Unknown/extra calls, duplicates, wrong operations, missed approvals,
  mismatched outcomes, missing nodes, cycles and wrong dependency order fail.
- File size <= 1 MiB, 256 nodes maximum, 1024 events maximum.
- Exit `0`: pass; `1`: violation; `2`: invalid policy/trace/file.
  CI must treat **all nonzero exits as failure**.

## Security and evidence boundary

The **host** must be the trusted trace emitter. The model must not produce,
alter, or declare the trace that is used to validate its own execution.
Do not include tool arguments, PII, credentials, or prompts in this minimal
trajectory projection. Verify run provenance and completeness separately.

An event labelled `approved` is an observation, not cryptographic proof of
founder approval. A passing trace does not prove all dispatch paths were
instrumented, nor does it grant or block authority. Runtime enforcement stays
with KCC Guard and the host's own authorization boundary. KCC execution
evidence can bind a trace digest but does not attest to its producer.

## Next

1. Connect trusted pre-dispatch and approval emitters in an isolated host demo.
2. Bind trace digest to execution/capsule identity; prove completeness.
3. Add adversarial tests for missing/forged/replayed events and retries.
4. Gate real PR execution only after trusted emission and owner approval.
