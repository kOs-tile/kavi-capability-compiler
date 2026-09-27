"""Cross-subsystem execution evidence references.

KCC remains the authority plane. This module only binds immutable references to
external evidence artifacts (context, memory, telemetry, extraction, domain
detectors) to an execution/capsule for later audit.
"""

from __future__ import annotations

import re
from typing import Any

from kavi_capability_compiler.core import digest


_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def evidence_ref(
    kind: str,
    producer: str,
    artifact_id: str,
    artifact_digest: str,
) -> dict[str, str]:
    kind = str(kind).strip().lower()
    producer = str(producer).strip().lower()
    artifact_id = str(artifact_id).strip()
    artifact_digest = str(artifact_digest).strip().lower()

    if not kind or not producer or not artifact_id:
        raise ValueError("Evidence reference fields must be non-empty")
    if not _HEX64.fullmatch(artifact_digest):
        raise ValueError("artifact_digest must be a lowercase SHA-256 hex digest")

    return {
        "kind": kind,
        "producer": producer,
        "artifact_id": artifact_id,
        "artifact_digest": artifact_digest,
    }


def build_execution_evidence(
    execution_id: str,
    capsule_id: str,
    evidence: list[dict[str, str]],
    *,
    capability_id: str | None = None,
    operation: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic audit envelope without granting authority."""
    execution_id = str(execution_id).strip()
    capsule_id = str(capsule_id).strip()

    if not execution_id:
        raise ValueError("execution_id is required")
    if not _HEX64.fullmatch(capsule_id):
        raise ValueError("capsule_id must be a canonical KCC SHA-256 capsule id")

    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for item in evidence:
        ref = evidence_ref(
            item.get("kind", ""),
            item.get("producer", ""),
            item.get("artifact_id", ""),
            item.get("artifact_digest", ""),
        )
        key = (
            ref["kind"],
            ref["producer"],
            ref["artifact_id"],
            ref["artifact_digest"],
        )
        if key not in seen:
            normalized.append(ref)
            seen.add(key)

    normalized.sort(
        key=lambda item: (
            item["kind"],
            item["producer"],
            item["artifact_id"],
            item["artifact_digest"],
        )
    )

    envelope: dict[str, Any] = {
        "version": "kcc.execution-evidence.v1",
        "execution_id": execution_id,
        "capsule_id": capsule_id,
        "capability_id": capability_id,
        "operation": operation,
        "evidence": normalized,
        "authority_granted": False,
        "authority_note": (
            "Evidence references are audit material only; runtime authority is "
            "defined by the bound KCC capsule and authorize_call()."
        ),
    }
    envelope["digest"] = digest(envelope)
    return envelope


def verify_execution_evidence(envelope: dict[str, Any]) -> dict[str, Any]:
    """Verify envelope integrity; does not verify the referenced artifacts themselves."""
    body = dict(envelope)
    claimed = body.pop("digest", None)
    checks = [
        ("version", body.get("version") == "kcc.execution-evidence.v1"),
        ("integrity", claimed == digest(body)),
        ("capsule_id", bool(_HEX64.fullmatch(str(body.get("capsule_id", ""))))),
        ("non_authority", body.get("authority_granted") is False),
    ]
    return {
        "valid": all(ok for _, ok in checks),
        "checks": [{"name": name, "ok": ok} for name, ok in checks],
    }
