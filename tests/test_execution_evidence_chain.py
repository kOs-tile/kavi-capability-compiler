from kavi_capability_compiler.core import (
    authorize_call,
    compile_capsule,
    digest,
    scan_mcp_snapshot,
)
from kavi_capability_compiler.evidence import (
    build_execution_evidence,
    evidence_ref,
    verify_execution_evidence,
)


SNAPSHOT = {
    "server": {"name": "browser"},
    "tools": [
        {
            "name": "browser_tabs",
            "description": "List, create, close, or select a browser tab.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tab_index": {"type": "integer"},
                },
            },
        }
    ],
}


def _artifact_ref(kind, producer, artifact_id, payload):
    return evidence_ref(
        kind=kind,
        producer=producer,
        artifact_id=artifact_id,
        artifact_digest=digest(payload),
    )


def _compiled_capsule():
    inventory = scan_mcp_snapshot(SNAPSHOT)
    capability_id = "mcp:browser:browser_tabs"
    intent = {
        "task": "Inspect existing browser tabs without mutating them",
        "capabilities": [capability_id],
        "ttl_seconds": 300,
        "capability_constraints": {
            capability_id: {
                "operations": ["list"],
                "parameters": {
                    "tab_index": {
                        "type": "integer",
                        "min": 0,
                        "max": 3,
                    }
                },
            }
        },
    }
    return compile_capsule(
        inventory,
        intent,
        {"default": "allow"},
        now=100,
    )


def test_cross_subsystem_evidence_cannot_expand_kcc_authority():
    capsule = _compiled_capsule()
    capability_id = "mcp:browser:browser_tabs"

    assert authorize_call(
        capsule,
        capability_id,
        operation="list",
        parameters={"tab_index": 2},
        now=101,
    )["allowed"] is True
    assert authorize_call(
        capsule,
        capability_id,
        operation="close",
        parameters={"tab_index": 2},
        now=101,
    )["reason"] == "operation_not_granted"

    evidence = [
        _artifact_ref(
            "capability_plan",
            "axiom",
            "plan-1",
            {"selected": [capability_id], "authority_granted": False},
        ),
        _artifact_ref(
            "context",
            "oracle",
            "state-1",
            {"trusted_data_pct": 100, "gas": "real"},
        ),
        _artifact_ref(
            "memory",
            "mnemos",
            "query-1",
            {"policy_leak_count": 0, "returned_memories": 3},
        ),
        _artifact_ref(
            "authority_observation",
            "spectraflow",
            "observation-1",
            {"within_claimed_authority": True},
        ),
        _artifact_ref(
            "browser_extraction",
            "phantom",
            "extract-1",
            {"passed": True, "required_coverage": 1.0},
        ),
        _artifact_ref(
            "domain_detection",
            "nephilim",
            "ethereum:19000001:sandwich",
            {"event_count": 1, "authorizes_action": False},
        ),
    ]

    envelope = build_execution_evidence(
        execution_id="exec-1",
        capsule_id=capsule["capsule_id"],
        evidence=evidence,
        capability_id=capability_id,
        operation="list",
    )

    assert verify_execution_evidence(envelope)["valid"] is True
    assert envelope["authority_granted"] is False
    assert len(envelope["evidence"]) == 6

    # Evidence can explain a later observed attempt to close a tab, but even a
    # valid evidence envelope cannot convert that operation into capsule authority.
    violating_observation = build_execution_evidence(
        execution_id="exec-2",
        capsule_id=capsule["capsule_id"],
        evidence=evidence,
        capability_id=capability_id,
        operation="close",
    )
    assert verify_execution_evidence(violating_observation)["valid"] is True
    assert violating_observation["authority_granted"] is False
    assert authorize_call(
        capsule,
        capability_id,
        operation="close",
        parameters={"tab_index": 2},
        now=101,
    )["allowed"] is False


def test_evidence_chain_is_bound_to_exact_capsule():
    first = _compiled_capsule()
    second = _compiled_capsule()

    # Same deterministic inputs and issuance time produce the same capsule.
    assert first["capsule_id"] == second["capsule_id"]

    changed = dict(second)
    changed["expires_at"] += 1
    changed["capsule_id"] = digest({k: v for k, v in changed.items() if k != "capsule_id"})
    assert first["capsule_id"] != changed["capsule_id"]

    envelope = build_execution_evidence(
        "exec-1",
        first["capsule_id"],
        [_artifact_ref("context", "oracle", "state-1", {"state": 1})],
    )
    assert envelope["capsule_id"] == first["capsule_id"]
    assert envelope["capsule_id"] != changed["capsule_id"]
