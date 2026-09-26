import copy

import pytest

from kavi_capability_compiler.evidence import (
    build_execution_evidence,
    evidence_ref,
    verify_execution_evidence,
)


CAPSULE_ID = "a" * 64


def ref(kind, producer, artifact_id, digest_char):
    return evidence_ref(kind, producer, artifact_id, digest_char * 64)


def test_execution_evidence_is_order_deterministic():
    refs = [
        ref("memory", "mnemos", "query-1", "b"),
        ref("context", "oracle", "state-1", "c"),
        ref("telemetry", "spectraflow", "event-1", "d"),
    ]

    first = build_execution_evidence("exec-1", CAPSULE_ID, refs)
    second = build_execution_evidence("exec-1", CAPSULE_ID, list(reversed(refs)))

    assert first["digest"] == second["digest"]
    assert first["evidence"] == second["evidence"]


def test_duplicate_evidence_references_are_collapsed():
    item = ref("browser", "phantom", "extract-1", "e")
    envelope = build_execution_evidence("exec-1", CAPSULE_ID, [item, item])

    assert len(envelope["evidence"]) == 1


def test_execution_evidence_cannot_claim_authority():
    envelope = build_execution_evidence(
        "exec-1",
        CAPSULE_ID,
        [ref("memory", "mnemos", "query-1", "b")],
        capability_id="mcp:browser:browser_tabs",
        operation="list",
    )

    assert envelope["authority_granted"] is False
    assert "authorize_call" in envelope["authority_note"]
    assert verify_execution_evidence(envelope)["valid"] is True


def test_tampered_evidence_envelope_fails_integrity():
    envelope = build_execution_evidence(
        "exec-1",
        CAPSULE_ID,
        [ref("context", "oracle", "state-1", "c")],
    )
    tampered = copy.deepcopy(envelope)
    tampered["evidence"][0]["artifact_id"] = "state-2"

    verification = verify_execution_evidence(tampered)

    assert verification["valid"] is False
    assert any(
        check["name"] == "integrity" and not check["ok"]
        for check in verification["checks"]
    )


def test_invalid_artifact_digest_fails_closed():
    with pytest.raises(ValueError, match="artifact_digest"):
        evidence_ref("memory", "mnemos", "query-1", "not-a-digest")


def test_invalid_capsule_id_fails_closed():
    with pytest.raises(ValueError, match="capsule_id"):
        build_execution_evidence("exec-1", "capsule-123", [])
