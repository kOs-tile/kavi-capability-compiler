# M3A — KAVI Control-Plane Dogfood

M3 begins with the real KAVI Shared Execution Control surface that is available in authoritative GitHub state.

Hermes itself does not currently expose a source-controlled capability registry in the shared repository, so KCC does not invent one. The first proving ground is the KAVI Dispatch Bridge contract.

## Authoritative source

Repository:
`kOs-tile/kavi-codex-state`

Contract:
`dispatch-bridge/bridge-contract.json`

Pinned source blob:
`80f521a9aba225bbc5abcb815feae24569fa8098`

Declared surface:
- `enqueue_task` — write
- `get_task_status` — read
- `get_operator_snapshot` — read
- `list_recent_tasks` — read
- `approve_task` — write

The adapter is optional and lives outside the compiler kernel. KCC remains framework-agnostic.

## Dogfood task

Task:

> Read the current KAVI operator snapshot without mutating execution state.

Standing authority:
**5 capabilities**

Compiled grant:
**1 capability — `get_operator_snapshot`**

Authority reduction:
**80%**

Runtime authorization evidence:
- granted read: **allowed**
- `enqueue_task`: **blocked — capability_not_granted**
- `approve_task`: **blocked — capability_not_granted**
- mutation capabilities in grants: **0**

No production task was enqueued and no approval mutation was attempted.

## Authority fingerprint rule

Source provenance and authority semantics are deliberately separate.

Changing only the source revision SHA does **not** change the capability fingerprints or semantic inventory digest.

Changing an actual declared authority field changes only the affected capability fingerprint.

This prevents source-control churn from becoming false authority drift while preserving provenance.

## Live deployment evidence

A production Vercel deployment of `kavi-dispatch-bridge` exists and reports:

- deployment state: READY
- target: production
- `GET /api/health`: HTTP 200
- service: `kavi-dispatch-bridge`
- version: `0.1.0`
- configured: `true`
- authority: `kOs-tile/kavi-codex-state`

Authenticated live `tools/list` was **not** performed in M3A because the bridge bearer value is not exposed through the connected Vercel read surface. KCC does not extract, print, or bypass that secret.

## Regression state

Recorded CI checkpoint:
- full test suite: **37 passed**
- live discovery integration suite: **11 passed**
- KAVI dogfood gate: PASS
- M1 dangerous recall: 100%
- M1 false-safe: 0
- M1 mean authority reduction: 99.49%
- M2 compatibility, drift, and holdout gates: PASS

## M3A verdict

**PASS.**

KCC can ingest the real KAVI control-plane authority declaration, reduce it to task-scoped authority, and enforce the compiled boundary before dispatch.

## Next

M3B has two independent paths:

1. **Live KAVI Bridge read-only discovery**
   - only when the existing bearer credential is available through an authorized connector/runtime;
   - run authenticated `initialize -> tools/list`;
   - compile the same read-only capsule from observed live authority;
   - do not call mutation tools.

2. **Hermes-local adapter**
   - only after an actual Hermes capability/tool export or registry is available;
   - do not derive a fake Hermes surface from chat history or unrelated KAVI state.


## M3B probe readiness

The authenticated live-observation path is now implemented without widening the
production bridge.

`kcc probe-kavi`:

1. requires an HTTPS MCP endpoint;
2. reads the bearer only from a named environment variable (default
   `KAVI_DISPATCH_TOKEN`);
3. performs only `initialize`, `tools/list`, and one read-only
   `get_operator_snapshot` call;
4. converts the observed live tool list into KCC inventory IR;
5. records the operator response only as source + SHA-256 digest, not raw snapshot;
6. emits a canonical `kcc.kavi-live-probe.v0` report fingerprint;
7. never returns or fingerprints bearer material;
8. exposes no CLI flag for passing the token value.

Current production health evidence was rechecked on September 26, 2026:

- endpoint: `https://kavi-dispatch-bridge.vercel.app/api/health`
- HTTP: 200
- `ok=true`
- service: `kavi-dispatch-bridge`
- version: `0.1.0`
- `configured=true`
- authority: `kOs-tile/kavi-codex-state`

The connected Vercel read surface does not expose the bridge bearer value, and
authoritative Shared Execution Control contains no immutable PASS result proving
the authenticated deployment-verification task ran. Therefore the authenticated
M3B observation remains **pending credential availability in an authorized secure
runtime**. It is not marked PASS from health metadata alone.

Secure runtime command:

```bash
KAVI_DISPATCH_TOKEN=... \
kcc probe-kavi \
  --endpoint https://kavi-dispatch-bridge.vercel.app/api/mcp \
  -o kavi-live-probe.json
```

The token should be injected by the runtime/secret store, not typed into shell
history or committed to a file.
