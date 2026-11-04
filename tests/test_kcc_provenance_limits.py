"""Version-aware revocation and deliberately exposed host bypass limits.

These tests are negative-evidence drills, NOT a claim of full host coverage.
"""
from __future__ import annotations

import kavi_capability_compiler as kcc
from examples.trajectory.cross_version_revocation_drill import run_drill
from scripts.trusted_trajectory import HostTraceRecorder, verify_host_bundle
from scripts.host_effect_reconcile import compare_trace_to_effects

PUBLIC_KEY = bytes.fromhex("91" * 32)

def test_revocation_contract_is_never_misreported_as_stable_feature():
    report = run_drill()
    assert report["synthetic_only"] is True
    assert report["host_attestation_valid"] is True
    assert report["authorized_dispatches"] == 1
    if kcc.__version__ == "0.1.1":
        assert report["version_feature_detected"] is False
        assert report["current_authority_contract"] == "host_required_not_tested_on_stable"
        assert report["pre_dispatch_denials"] == 0
        assert report["event_count"] == 1
    else:
        assert kcc.__version__ == "0.2.0"
        assert report["version_feature_detected"] is True
        assert report["current_authority_contract"] == "verified_local_v0.2"
        assert report["pre_dispatch_denials"] == 3
        assert report["event_count"] == 4
        assert report["denial_reasons"] == {
            "revoked": "current_authority_revoked",
            "unknown": "current_authority_unknown",
            "resolver_error": "current_authority_resolver_error",
        }

def test_signed_guard_trace_does_not_prove_absence_of_unguarded_host_path():
    """Intentionally bypass the recorder to falsify an overbroad coverage claim."""
    tools = {"tools": [
        {"name": "read_record", "description": "Read synthetic record", "input_schema": {"type": "object", "properties": {}}},
        {"name": "delete_record", "description": "Delete synthetic record", "input_schema": {"type": "object", "properties": {}}},
    ]}
    inventory = kcc.scan_manifest(kcc.adapt_capabilities(
        "generic", tools, namespace="provenance-negative-demo"))
    names = {x["name"]: x["id"] for x in inventory["capabilities"]}
    capsule = kcc.compile_capsule(inventory, {
        "task": "Read a record, never delete",
        "capabilities": [names["read_record"]],
        "ttl_seconds": 300,
    }, {"default": "allow"}, now=100)
    assert capsule["status"] == "ready"
    guard = kcc.Guard.from_capsule(capsule, inventory=inventory)
    recorder = HostTraceRecorder(
        execution_id="test-uncovered-path",
        capsule_id=capsule["capsule_id"],
        emitter_id="test-host-with-uncovered-dispatch",
        signing_key=PUBLIC_KEY,
    )
    # This is the independently held synthetic *effect* ledger, not model text.
    effects = []
    def host_dispatch(capability, params):
        effects.append({"capability": capability, "params": dict(params),
                        "capability_id": names[capability],
                        "operation": "read" if capability == "read_record" else "delete"})
        return {"synthetic": True}

    result = recorder.guarded_call(
        node_id="allowed_read",
        guard=guard,
        capability_id=names["read_record"],
        operation="read",
        parameters={},
        dispatcher=lambda params: host_dispatch("read_record", params),
        now=101,
    )
    assert result["executed"] is True
    assert len(effects) == 1

    # Deliberate host integration error: a second path invokes dispatcher
    # directly. This is NOT an exploit against KCC or a remote system.
    host_dispatch("delete_record", {})
    assert [x["capability"] for x in effects] == ["read_record", "delete_record"]

    bundle = recorder.finalize()
    assert verify_host_bundle(
        bundle,
        signing_key=PUBLIC_KEY,
        execution_id="test-uncovered-path",
        capsule_id=capsule["capsule_id"],
        emitter_id="test-host-with-uncovered-dispatch",
    )["valid"] is True

    recorded_dispatches = bundle["attestation"]["dispatch_count"]
    assert recorded_dispatches == 1  # The HMAC is valid, but does not know delete occurred.
    assert len(effects) == 2
    unobserved_effects = len(effects) - recorded_dispatches
    assert unobserved_effects == 1  # Independent ledger reveals coverage gap.

    # HMAC validation still succeeds; independently captured local effects
    # contradict the incomplete signed trajectory.
    missing = compare_trace_to_effects(bundle, None)
    assert missing["status"] == "UNVERIFIED"
    reconciled = compare_trace_to_effects(bundle, effects)
    assert reconciled["status"] == "COVERAGE_GAP"
    assert reconciled["unobserved_effect_count"] == 1
    assert reconciled["phantom_trace_count"] == 0
    assert reconciled["unobserved_effect_kinds"] == [
        {"capability_id": names["delete_record"], "operation": "delete", "count": 1}
    ]
