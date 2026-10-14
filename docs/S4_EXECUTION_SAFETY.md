# S4/S5: Approval receipts, durable replay barrier, synthetic host CI

> **Scope:** isolated, synthetic test host only. No production approval integration,
> Hermes cutover, actual email sending, financial order placement, or guarantee
> that every external dispatcher is instrumented.

## What is implemented

\`scripts/approval_and_journal.py\` adds two independent host controls:

### 1. Host-owned scoped approval receipts

The reference \`kcc.approval-receipt.v0\` contains an exact
\`execution_id\`, \`capsule_id\`, \`step_id\`, \`capability_id\`,
\`operation\`, \`actor_id\`, \`decision: approved\`, \`issued_at\` and
\`expires_at\`. HMAC-SHA256 authenticates the canonical bytes.

The runtime verifier requires externally supplied expected identities and
independently trusted signing key, enforces issuance/expiry and a maximum
five-minute lifetime, and rejects malformed, manipulated, mismatched,
wrong-actor and wrong-step receipts. \`HostTraceRecorder.record_signed_approval\`
emits \`approval/approved\` **only after receipt verification**; KCC's
\`ApprovalRequired\` remains \`denial/denied\` as in the earlier v0 example.

**Important:** The test receipt helper and keys are public synthetic
fixtures. They do not constitute a real human approval. A production
mobile-founder approval requires separate authenticated identity, tamper-proof
receipt issuance, key ownership, revocation, replay control and audit storage.

### 2. Durable host idempotency barrier

\`DurableDispatchJournal\` writes a \`started\` record to SQLite in WAL
mode with \`synchronous=FULL\` and a unique \`(execution_id, step_id)\`
constraint **before dispatch**. Request fingerprint binds capsule, requested
operation, arguments and approval MAC.

- First valid request: reserve step, independently verify approval when
  host policy requires it, then KCC Guard authorizes exactly before the
  actual host dispatcher.
- Completed request replay with identical fingerprint: return stored result
  **without dispatching again**.
- Existing \`started\` (including after process crash): return
  \`AmbiguousOutcome\`; never assume the prior side effect did not happen.
- Same step with different parameters/authority: \`JournalConflict\`.
- Guard denial: host recorder verifies the dispatcher was never entered.
  Denial is stored as terminal, and the dispatcher runs zero times.
- A dispatcher exception, process exit, disk failure after the external
  action, or incomplete journal commit is **not** automatically retried.

The journal is a conservative local crash barrier, **not** a general
exactly-once distributed execution protocol. External writes remain
at-least-once or ambiguous unless the downstream API provides an idempotency
key or independent reconciliation. Host storage durability and backup policy
must be evaluated separately.

### 3. CI from actual KCC Guard calls

The dedicated \`trusted-trajectory-dogfood\` workflow runs:

- Standalone DAG, host trace, and approval/journal regression tests.
- A **real KCC Guard** using only an in-memory synthetic message dispatcher.
- Missing approval -> zero dispatches.
- Signed public *test* approval -> precisely one successful dispatch.
- SQLite journal close/reopen -> no second dispatch.
- Host-created \`approval -> dispatch\` trace, HMAC attestation and policy DAG.
- Trace verification by a separate command using expected run identity.
- Wrong execution ID/cross-run replay and manipulated host trace MUST fail.
- Existing S3 synthetic host example still confirms denied deletion and
  \`approval_required\` outbound message both dispatch zero times.

These are meaningful integration and regression tests but cannot certify
that an arbitrary user's live agent host routes every side effect through
KCC. Nothing runs on Hermes production.

## Risk and explicit unsolved work

1. **Host compromise:** Same-process code controlling signing keys can forge
   events. Separate IAM/key service and privileged agent sandbox needed.
2. **Missing dispatch path:** Caller can bypass a wrapper if the host exposes
   another dispatcher. Each real integration requires exhaustive dispatcher
   inventory, strict enforcement at the host boundary and independent tests.
3. **Approval lifecycle:** Reference HMAC receipt does not prove a human was
   authenticated, was present, or did not revoke consent. A real approval
   provider is still missing.
4. **Crash/retry:** A crash after the remote side effect but before journal
   completion deliberately freezes the step. Safe reconciliation requires
   downstream idempotency keys/transaction IDs, operator workflow and durable
   cross-process state.
5. **Scope:** Only synchronous local Python dispatcher is modeled; async
   workers, race conditions across hosts, distributed databases, and
   delayed/queued operations remain separate engineering projects.
6. **Evidence integrity:** A trace hash and MAC prove exact attested bytes
   under the test key, not trustworthy run completeness absent a trusted
   independent emitter and verifier.

## Exit criteria for production integration

A future target runtime must document **all** side-effect dispatcher entry
points and their IAM, show the agent cannot write the recorder or control
its keys, verify authenticated mobile approval from an independent authority,
provide an end-to-end idempotency/reconciliation contract, and pass
infrastructure restart/backup/restore and adversarial fault-injection tests.

Do not set a production required status check or enable real-money/email
automations based solely on this synthetic PR. Keep PR #104 as DRAFT until
the code review and full matrix are verified; Hermes Phoenix remains an
independent prerequisite to any Hermes cutover.
