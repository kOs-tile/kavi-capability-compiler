# Execution evidence envelope

KCC is the authority plane. External systems may produce evidence that explains context, retrieval, telemetry, tool results, runtime observations, or domain signals associated with an execution. Those artifacts do not grant authority.

`kcc.execution-evidence.v1` binds immutable evidence references to one execution and one canonical KCC capsule by digest.

## Contract

```json
{
  "version": "kcc.execution-evidence.v1",
  "execution_id": "exec-123",
  "capsule_id": "<64-char KCC capsule SHA-256>",
  "capability_id": "kcc:crm:read_customer",
  "operation": "read",
  "evidence": [
    {
      "kind": "retrieval",
      "producer": "host-rag",
      "artifact_id": "query-123",
      "artifact_digest": "<64-char SHA-256>"
    },
    {
      "kind": "runtime_observation",
      "producer": "host-telemetry",
      "artifact_id": "trace-456",
      "artifact_digest": "<64-char SHA-256>"
    }
  ],
  "authority_granted": false,
  "authority_note": "Evidence references are audit material only; runtime authority is defined by the bound KCC capsule and authorize_call().",
  "digest": "<envelope SHA-256>"
}
```

The envelope stores references and digests, not full evidence payloads.

## Producer contract

KCC does not require a fixed producer list.

Any host subsystem may contribute evidence if it can provide:

- `kind`
- `producer`
- `artifact_id`
- lowercase SHA-256 `artifact_digest`

Examples include retrieval systems, model routers, telemetry pipelines, browser extractors, policy analyzers, workflow engines, and domain-specific detectors.

## Verification boundary

`verify_execution_evidence(...)` verifies:

- envelope version
- envelope integrity
- canonical capsule ID shape
- the invariant that the envelope itself grants no authority

It does **not** fetch or verify referenced artifacts. A full audit verifier may resolve those artifacts and recompute their digests separately.

## Safety invariant

**Evidence may explain an execution; evidence may not expand an execution.**

An external signal may affect planning or trigger approval, but it cannot create a grant absent from the KCC capsule.

## CLI

Bind evidence references to an already-compiled capsule:

```bash
kcc evidence-bind capsule.json \
  --execution-id exec-123 \
  --evidence evidence-refs.json \
  --capability kcc:crm:read_customer \
  --operation read \
  -o execution-evidence.json
```

Verify the envelope itself:

```bash
kcc evidence-verify execution-evidence.json
```

`evidence-verify` exits non-zero when the envelope version, integrity, capsule ID shape, or non-authority invariant fails.

Producer artifact verification remains a host-owned responsibility.
