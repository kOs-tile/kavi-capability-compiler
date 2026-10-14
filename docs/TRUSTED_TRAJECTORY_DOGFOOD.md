# Trusted host trajectory evidence — experimental, synthetic dogfood

This builds on the separate deterministic DAG checker in [TRAJECTORY_CI_V0.md](TRAJECTORY_CI_V0.md). No KCC core, release, Guard or Hermes production code is changed.

## Verified scope

1. A host-owned \`HostTraceRecorder\` accepts an **existing KCC Guard** and a host-supplied dispatcher. It delegates through \`Guard.dispatch_sync\`, records \`dispatch/executed\` **only after** the actual host dispatcher succeeds, and records \`denial/denied\` only when KCC denies *before* dispatcher entry.
2. Unexpected dispatcher failure makes the recorder non-finalizable. A dispatcher throwing its own \`AuthorityDenied\` can never masquerade as a pre-dispatch Guard denial.
3. One finalized event trace is hashed using deterministic canonical JSON. A separate HMAC-SHA256 host attestation binds that digest, a host execution ID, an exact KCC capsule ID, host emitter identity, event count and completed-dispatch count.
4. The independent verifier requires the key and **expected execution/capsule/emitter identity from outside the bundle**. It rejects altered traces, mismatched HMACs, cross-run/capsule/emitter replay, and mismatched counts before evaluating the expected DAG.
5. The synthetic dogfood exercises the real KCC embedded Guard with a synthetic customer record: read dispatch once, customer deletion dispatch zero, outbound send dispatch zero because \`approval_required\`. It binds the resulting trajectory digest to an existing non-authoritative KCC execution evidence envelope; its referenced artifact digest is compared against the attested trace digest.

## Local execution

\`\`\`sh
python -m pip install -e . pytest
python -m pytest -q tests/test_trajectory_ci.py tests/test_trusted_trajectory.py

python -m examples.trajectory.trusted_host_dogfood \
  --output /tmp/kcc-host-bundle.json \
  --policy-output /tmp/kcc-host-policy.json \
  --evidence-output /tmp/kcc-host-evidence.json

# Public synthetic fixture key ONLY; never use for live telemetry.
export KCC_TRACE_ATTEST_KEY_HEX="$(python -c 'print("1b"*32)')"
capsule="$(python -c 'import json; print(json.load(open("/tmp/kcc-host-evidence.json"))["summary"]["capsule_id"])')"
python -m scripts.trusted_trajectory \
  --policy /tmp/kcc-host-policy.json \
  --bundle /tmp/kcc-host-bundle.json \
  --execution-id synthetic-run-001 \
  --capsule-id "$capsule" \
  --emitter-id kcc-synthetic-host
\`\`\`

CLI exit codes: \`0\` attested trace and DAG passed; \`1\` authenticated trace violates expected DAG; \`2\` provenance/shape/identity invalid. CI must reject either nonzero exit code. The dedicated \`trusted-trajectory-dogfood\` GitHub Action verifies a valid real-Guard synthetic run and deliberately tampers with an observed operation to verify rejection.

## Scope of the S1/S2/S3 slice

- S1 host event projection: \`kind, capability_id, operation, outcome, node_id\`. No raw parameters, model output, prompt, credentials, or customer data.
- S2 test-host integration: a **real Guard** and a real local Python dispatcher that touches only synthetic in-memory counters. No Hermes, third-party or network actions.
- S3 integrity binding: host HMAC attestation plus non-authoritative \`kcc.execution-evidence.v1\` artifact reference to the trace digest.

**Important limitations**

- HMAC is only meaningful if verifier key management and trusted host isolation are independent of the agent. This repository's test key is intentionally public, so *test results are not production attestation*.
- A signed \`complete: true\` is host's assertion about the instrumented path, not proof that a separate uninstrumented dispatcher cannot exist.
- The recorder supports **synchronous** dispatch only; async, concurrency, crash-safe spool/atomic write, retries, and durable storage require separate design and tests.
- An attested denial means Guard rejected a call *before this wrapper's dispatcher*. It does not attest every other runtime/tool path.
- An observed \`ApprovalRequired\` is a **denial**, not proof of human approval. This v0 deliberately provides **no approval event emitter**. Actual human approval must come from a trusted host authority with a verifiable approval receipt in a later slice.
- HMAC and trace integrity do not replace real authentication, permissions, signed KCC capsules, trusted signer provisioning or dispatcher-level access controls.
- An attacker controlling the host process or its signing key can forge observations. The model/agent must never control the host trace emitter or verifier secrets.
- Partial crashes/host exits cannot be detected merely by an absent JSON file: the real workflow must independently enforce that the expected trace artifact exists, matches the execution and is complete before accepting a run.

## Remaining for production

S4: trusted approval receipts, interrupted run/retry/resume, host-to-verifier key boundaries, evidence storage durability, malformed/proprietary data, bypass coverage audit. S5: integration into a real runtime PR path with genuine host-generated artifact and controlled mandatory status check. No Hermes Phoenix cutover until its independent closure gates are passed.
