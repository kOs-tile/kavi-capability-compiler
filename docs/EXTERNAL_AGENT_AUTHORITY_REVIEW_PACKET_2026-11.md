# External Review Packet — KCC Agent Authority & Evidence Boundaries
_2026-11-02 · Synthetic-only research · No production security certification_

## What we are asking independent reviewers to falsify

KAVI Capability Compiler (KCC) is an open-source task-scoped authorization compiler for agent tools. It normalizes tool definitions, emits a bounded capsule and asks a host to place a Guard immediately before its real side-effect dispatcher. Our current **narrow** claims are:

1. A task-scoped allow reaches a synthetic dispatcher exactly once.
2. Six ungranted/invalid tool-call conditions are denied before dispatch.
3. Stable release and development package were installed separately in CI; import sources were asserted.
4. A Guard decision alone cannot prove **all** host side effects route through Guard.
5. HMAC-attested trace integrity alone cannot prove **completeness** if some host path bypasses the recorder.

Reviewers should aim to disprove one of these claims with a minimal synthetic host integration, rather than merely reproduce green tests.

## Exact code and verification

| Artifact | Purpose |
|---|---|
| [v0.1.1 release](https://github.com/kOs-tile/kavi-capability-compiler/releases/tag/v0.1.1) | Stable published baseline; not v0.2 |
| [Draft #104](https://github.com/kOs-tile/kavi-capability-compiler/pull/104) | Experimental host trajectory, signed test trace and approval journal |
| [Stacked draft #109](https://github.com/kOs-tile/kavi-capability-compiler/pull/109) | Actual KCC Guard synthetic scenarios and isolated version matrix |
| [Draft #107](https://github.com/kOs-tile/kavi-capability-compiler/pull/107) | Non-authoritative offline repeatability/evidence quality gate |
| [CI: stable vs dev](https://github.com/kOs-tile/kavi-capability-compiler/actions/runs/41560723699) | Both packages from separate sources; success through 2026-11-02 |
| [Issue #94](https://github.com/kOs-tile/kavi-capability-compiler/issues/94) | External validation cohort |
| [Issue #103](https://github.com/kOs-tile/kavi-capability-compiler/issues/103) | Independent challenge invitation |

### Engineering observations — NOT a model security score

For each separately installed KCC version, 10 deterministic replays of one synthetic host scenario yield 10 permitted reads, 60 blocked tool proposals and zero unauthorized instrumented dispatches. Cases cover ungranted delete, cross-tenant parameter, missing approval, post-compile inventory drift, unexpected tool argument, and expired capsule. An HMAC-signed recorder emits local evidence.

The v0.2 development line additionally supports **current_authority_resolver**. In a separate synthetic drill, revocation, unknown authority and resolver exceptions are blocked before dispatch. This is **not** a feature of stable v0.1.1; on stable, live revocation enforcement remains the host's responsibility.

### Explicit negative counterexample: signed trace is incomplete

\`tests/test_kcc_provenance_limits.py\` demonstrates an integration error:
- a legitimate read passes through Guard + HostTraceRecorder;
- an additional *synthetic* delete calls the host dispatcher directly;
- the trace's HMAC remains valid and includes only the recorded read;
- an independently captured local side-effect ledger includes both read and delete;
- \`scripts/host_effect_reconcile.py\` reports **COVERAGE_GAP**.

With **no** separate side-effect ledger, the reconciler returns **UNVERIFIED**, never PASS. Even matching counts cannot certify full coverage, causality, IAM, trusted key custody or remote completion. Host instrumentation must be exhaustive and independently protected.

## Minimal independent review protocol

1. Pick one exact revision of **stable** v0.1.1 and the current **draft** PR #109, and preserve install/import provenance. Avoid confusing the KCC release with the current v0.2 repository.
2. Bring your own tiny, synthetic-only host that uses a *real* dispatcher function (not a model's declaration that a tool ran).
3. Inventory all host side-effect entry points, including any direct import or function alias path that bypasses the Guard.
4. Add one permitted tool call and one forbidden tool call, then measure real effects at the dispatcher. Check parameters, tenant identity, tool authority drift and approval revocation.
5. Challenge host trace keys and ledger custody: which process can modify them? What happens after crash/restart? Can a missing recorder event be detected by an independent host log?
6. Report expected versus observed calls, exact commit and Python/runtime version, a minimized redacted reproduction and counterexample or negative result.
7. **Do not** send secrets, customer data, proprietary manifests, actual user records, or live payment/email side effects.

Suggested commands from PR #109 (Python 3.11, isolated environment):

\`\`\`bash
python -m pytest -o pythonpath=. -q \
  tests/test_kcc_safety_cases.py \
  tests/test_kcc_provenance_limits.py
python -m examples.trajectory.kcc_safety_cases --repeat 10
python -m examples.trajectory.cross_version_revocation_drill
\`\`\`

Import isolation matters: repository pytest defaults add \`src/\` to PYTHONPATH; use the version-asserting GitHub Action matrix rather than trusting an unverified local environment.

## Highest-value reviewer feedback

- A reproducible denied call that **does** reach a legitimate host dispatcher.
- A valid task that KCC overblocks due to missing or incorrect semantics.
- A tool-surface drift or actor-revocation condition incorrectly accepted.
- A host-path coverage counterexample that escapes current test instrumentation.
- A practical integration friction that would stop an OSS maintainer from adopting KCC.

**External cohort acceptance:** at least three independent builders, two different host/runtime shapes and at least one real dispatcher-boundary evidence report. KAVI-originated synthetic CI does **not** satisfy these criteria. As of this packet, independent reviews have **not** been verified as complete.

## Reporting channel

Non-security integration friction and non-sensitive false positives: [Issue #103](https://github.com/kOs-tile/kavi-capability-compiler/issues/103). A flaw that can forge capsule trust, bypass Guard with protected operations, bypass approvals or expose secrets should go through GitHub's **private vulnerability reporting / security advisory**, not a public comment. Do not disclose any real OpenAI vulnerability in this repository; use OpenAI's authorized bug bounty/private disclosure channel.

## Boundaries / what NOT to claim

No OpenAI infrastructure or ChatGPT systems were probed. No live LLM inference was performed, no actual prompt-injection success rate measured, and no third-party security attestation, OpenAI hiring offer, grant or bounty award has occurred. Ten deterministic replays are not ten independent natural-language attack samples. The experimental HMAC signer is a public test fixture; it is not production identity or nonrepudiation.

## Before merging drafts

- Host/recorder trust-root review for PR #104.
- CI coverage for malformed/cross-run traces, replays, missing observed side effects, valid-task false blocks and change-of-authority.
- Safe architectural review of any production host before enabling enforcement; no automatic Hermes deployment.
- Distinguish simulated host evidence from externally reproduced vulnerabilities.
