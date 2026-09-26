# Execution evidence envelope

KCC is the authority plane. Other KAVI subsystems may produce evidence that
explains the context, memory, browser result, runtime behavior, or domain signal
associated with an execution, but those artifacts do not grant authority.

`kavi.execution-evidence.v0` binds those artifacts to one execution and one
canonical KCC capsule by digest.

## Contract

```json
{
  "version": "kavi.execution-evidence.v0",
  "execution_id": "exec-123",
  "capsule_id": "<64-char KCC capsule SHA-256>",
  "capability_id": "mcp:browser:browser_tabs",
  "operation": "list",
  "evidence": [
    {
      "kind": "capability_plan",
      "producer": "axiom",
      "artifact_id": "plan-123",
      "artifact_digest": "<AXIOM plan_fingerprint>"
    },
    {
      "kind": "context",
      "producer": "oracle",
      "artifact_id": "state-2026-09-26T17:00:00Z",
      "artifact_digest": "<ORACLE evidence_digest>"
    },
    {
      "kind": "memory",
      "producer": "mnemos",
      "artifact_id": "query-123",
      "artifact_digest": "<MNEMOS admission_fingerprint>"
    },
    {
      "kind": "authority_observation",
      "producer": "spectraflow",
      "artifact_id": "observation-123",
      "artifact_digest": "<SPECTRAFLOW evaluation_fingerprint>"
    },
    {
      "kind": "browser_extraction",
      "producer": "phantom",
      "artifact_id": "extract-123",
      "artifact_digest": "<PHANTOM report_fingerprint>"
    },
    {
      "kind": "domain_detection",
      "producer": "nephilim",
      "artifact_id": "ethereum:19000001:sandwich",
      "artifact_digest": "<NEPHILIM report_fingerprint>"
    }
  ],
  "authority_granted": false,
  "authority_note": "Evidence references are audit material only; runtime authority is defined by the bound KCC capsule and authorize_call().",
  "digest": "<envelope SHA-256>"
}
```

The envelope is intentionally small. It stores references and canonical digests,
not the full evidence payloads.

## Producer mapping

| Producer | Evidence artifact | Digest |
|---|---|---|
| AXIOM | pre-authority capability plan binding snapshot + intent | `plan_fingerprint` |
| ORACLE | provenance/freshness ledger | `evidence_digest` |
| MNEMOS | memory admission audit | `admission_fingerprint` |
| SPECTRAFLOW | authority-drift evaluation | `evaluation_fingerprint` |
| PHANTOM | extraction or extraction-drift report | `report_fingerprint` |
| NEPHILIM | detector evidence bound to normalized block inputs | `report_fingerprint` |

## Verification boundary

`verify_execution_evidence(...)` verifies:

- envelope version
- envelope integrity
- canonical capsule ID shape
- the invariant that the envelope itself grants no authority

It does **not** fetch or verify the referenced artifacts. A full verifier must
resolve each producer artifact, recompute its digest, and separately verify the
KCC capsule before accepting the audit chain.

## Safety invariant

**Evidence may explain an execution; evidence may not expand an execution.**

A memory, market signal, browser extraction, drift alert, or world-state value
can affect planning or trigger approval, but cannot create a grant absent from
the KCC capsule.


## CLI

Bind producer references to an already-compiled capsule:

```bash
kcc evidence-bind capsule.json \
  --execution-id exec-123 \
  --evidence evidence-refs.json \
  --capability mcp:browser:browser_tabs \
  --operation list \
  -o execution-evidence.json
```

Verify the envelope itself:

```bash
kcc evidence-verify execution-evidence.json
```

`evidence-verify` exits non-zero when the envelope version, integrity, capsule ID
shape, or non-authority invariant fails. Producer artifact verification remains a
separate producer-specific responsibility.
