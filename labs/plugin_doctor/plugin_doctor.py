from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import kavi_capability_compiler as kcc
from kavi_capability_compiler.core import audit_inventory

REPORT_VERSION = "plugin-doctor.report.v0"

OPENAI_PLUGIN_GUIDELINES = "https://developers.openai.com/plugins/plugin-guidelines"
OPENAI_PLUGIN_REVIEW = "https://developers.openai.com/plugins/deploy/app-review"

_DEDUCTIONS = {
    "critical": 35,
    "high": 15,
    "medium": 6,
    "low": 2,
}


@dataclass(frozen=True)
class DoctorFinding:
    code: str
    severity: str
    category: str
    message: str
    capability: str | None = None
    blocker: bool = False
    remediation: str | None = None
    source_url: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "capability": self.capability,
            "blocker": self.blocker,
            "remediation": self.remediation,
            "source_url": self.source_url,
        }


def _doctor_findings(inventory: dict[str, Any]) -> list[DoctorFinding]:
    findings: list[DoctorFinding] = []
    required_annotation_keys = ("readOnlyHint", "destructiveHint", "openWorldHint")

    for capability in inventory.get("capabilities", []):
        cid = capability.get("id")
        description = (capability.get("description") or "").strip()
        schema = capability.get("input_schema") or {}
        effect = capability.get("effect")
        analysis = capability.get("analysis") or {}
        risk_flags = set(analysis.get("risk_flags") or [])
        annotations = capability.get("annotations") or {}

        if not description:
            findings.append(
                DoctorFinding(
                    code="PD-OAI-D001",
                    severity="high",
                    category="openai_review",
                    capability=cid,
                    blocker=True,
                    message="Tool has no model-facing description.",
                    remediation="Add a nonempty description that accurately explains purpose, behavior, relevant limitations, and side effects.",
                    source_url=OPENAI_PLUGIN_GUIDELINES,
                )
            )
        elif len(description) < 24:
            findings.append(
                DoctorFinding(
                    code="PD-D002",
                    severity="medium",
                    category="discovery",
                    capability=cid,
                    message="Tool description is unusually thin for reliable model selection.",
                    remediation="Describe when the tool should be used, what it changes or returns, and its important boundaries.",
                )
            )

        missing_annotations = [
            key
            for key in required_annotation_keys
            if key not in annotations or not isinstance(annotations.get(key), bool)
        ]
        if missing_annotations:
            findings.append(
                DoctorFinding(
                    code="PD-OAI-A001",
                    severity="high",
                    category="openai_review",
                    capability=cid,
                    blocker=True,
                    message="Tool is missing explicit boolean OpenAI review annotations: "
                    + ", ".join(missing_annotations),
                    remediation="Set readOnlyHint, destructiveHint, and openWorldHint explicitly to true or false.",
                    source_url=OPENAI_PLUGIN_GUIDELINES,
                )
            )

        if not schema:
            findings.append(
                DoctorFinding(
                    code="PD-Q001",
                    severity="high",
                    category="schema",
                    capability=cid,
                    blocker=True,
                    message="Tool has no bounded input schema.",
                    remediation="Provide an explicit JSON Schema for all accepted arguments.",
                )
            )
        elif schema.get("type") == "object" and not isinstance(schema.get("properties"), dict):
            findings.append(
                DoctorFinding(
                    code="PD-Q002",
                    severity="medium",
                    category="schema",
                    capability=cid,
                    message="Object input schema does not declare properties.",
                    remediation="Declare the accepted object properties and required fields.",
                )
            )

        if effect == "unknown":
            findings.append(
                DoctorFinding(
                    code="PD-S001",
                    severity="high",
                    category="safety",
                    capability=cid,
                    blocker=True,
                    message="Capability authority/effect is unknown.",
                    remediation="Clarify the action semantics or source metadata so authority can be classified without guessing.",
                )
            )

        if "annotation_conflict" in risk_flags:
            findings.append(
                DoctorFinding(
                    code="PD-S002",
                    severity="high",
                    category="safety",
                    capability=cid,
                    blocker=True,
                    message="Declared annotations conflict with observed tool semantics.",
                    remediation="Correct the annotations or rename/rewrite the tool so declared and observed semantics agree.",
                    source_url=OPENAI_PLUGIN_GUIDELINES,
                )
            )

        if effect in {"delete", "execute", "financial", "deploy"}:
            findings.append(
                DoctorFinding(
                    code="PD-R001",
                    severity="high",
                    category="review",
                    capability=cid,
                    message=f"High-impact capability detected: {effect}.",
                    remediation="Require narrow schemas, explicit user intent, and an appropriate confirmation/approval boundary before execution.",
                    source_url=OPENAI_PLUGIN_GUIDELINES,
                )
            )
        elif effect in {"write", "external_message"}:
            findings.append(
                DoctorFinding(
                    code="PD-R002",
                    severity="medium",
                    category="review",
                    capability=cid,
                    message=f"Mutating capability detected: {effect}.",
                    remediation="Verify that the write boundary is explicit, minimally scoped, and testable.",
                    source_url=OPENAI_PLUGIN_GUIDELINES,
                )
            )

    return findings


def audit_source(
    source_format: str,
    payload: dict[str, Any],
    *,
    namespace: str,
    server: str | None = None,
) -> dict[str, Any]:
    """Produce a deterministic Plugin Doctor V0 static-readiness report."""

    manifest = kcc.adapt_capabilities(
        source_format,
        payload,
        namespace=namespace,
        source_metadata={"product": "kavi-plugin-doctor"},
        server=server,
    )
    inventory = kcc.scan_manifest(manifest)
    kcc_audit = audit_inventory(inventory)

    doctor = _doctor_findings(inventory)
    doctor_rows = [finding.as_dict() for finding in doctor]

    kcc_rows = []
    for finding in kcc_audit.get("findings", []):
        severity = finding.get("severity", "medium")
        kcc_rows.append(
            {
                "code": finding.get("code"),
                "severity": severity,
                "category": "authority",
                "message": finding.get("message"),
                "capability": finding.get("capability"),
                "blocker": finding.get("code") == "KCC-A100",
                "remediation": "Resolve the underlying authority ambiguity before shipping."
                if finding.get("code") == "KCC-A100"
                else None,
                "source_url": None,
            }
        )

    findings = kcc_rows + doctor_rows
    score = max(
        0,
        100
        - sum(_DEDUCTIONS.get(row.get("severity", "medium"), 6) for row in findings),
    )
    blocked = any(bool(row.get("blocker")) for row in findings)
    state = "BLOCKED" if blocked else ("FIX" if findings else "SHIP")

    return {
        "version": REPORT_VERSION,
        "state": state,
        "score": score,
        "summary": {
            "capabilities": len(inventory.get("capabilities", [])),
            "findings": len(findings),
            "blockers": sum(1 for row in findings if row.get("blocker")),
        },
        "inventory_digest": inventory.get("digest"),
        "findings": findings,
        "rule_sources": [
            OPENAI_PLUGIN_GUIDELINES,
            OPENAI_PLUGIN_REVIEW,
        ],
        "disclaimer": "V0 is a deterministic static-readiness heuristic. Source-linked checks reflect published rules, but the score does not guarantee OpenAI approval, placement, or distribution.",
    }
