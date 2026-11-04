"""Cross-version authority revocation drill with a real KCC Guard and a synthetic host.

Stable v0.1.1 deliberately has no current_authority_resolver; this runner must
report that boundary as HOST_REQUIRED, not silently pretend it was tested.
Unreleased v0.2 tests revocation/unknown/resolver-error fail-closed behavior.

No OpenAI requests, real accounts, production approvals or external effects.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import kavi_capability_compiler as kcc
from scripts.trusted_trajectory import HostTraceRecorder, verify_host_bundle
from scripts.trajectory_ci import evaluate

PUBLIC_TEST_HMAC_KEY = bytes.fromhex("81" * 32)
EMITTER = "kcc-revocation-synthetic-host"


def run_drill() -> dict:
    manifest = kcc.adapt_capabilities("generic", {"tools": [{
        "name": "update_record",
        "description": "Update one synthetic record, host-authority required",
        "input_schema": {"type": "object", "properties": {
            "record_id": {"type": "string"}, "value": {"type": "string"}},
            "required": ["record_id", "value"]},
    }]}, namespace="kcc-revocation-eval")
    inventory = kcc.scan_manifest(manifest)
    cid = inventory["capabilities"][0]["id"]
    capsule = kcc.compile_capsule(
        inventory,
        {"task": "Update only a synthetic assigned record",
         "capabilities": [cid],
         "ttl_seconds": 300,
         "capability_constraints": {cid: {
             "operations": ["update"],
             "parameters": {
                 "record_id": "synthetic-1",
                 "value": {"type": "string", "max_length": 32},
             },
         }}},
        {"default": "allow"}, now=100,
    )
    if capsule["status"] != "ready":
        raise AssertionError(f"unexpected capsule status: {capsule['status']}")

    calls = []
    def dispatcher(params):
        calls.append(dict(params))
        return {"synthetic": True}

    state = {"active": True, "reason": "active"}
    resolver_calls = []
    def current_authority_resolver(context):
        resolver_calls.append(dict(context))
        if state.get("fault"):
            raise RuntimeError("synthetic control-plane failure")
        return dict(state)

    supports_resolver = "current_authority_resolver" in inspect.signature(
        kcc.Guard.from_capsule).parameters
    kw = {"inventory": inventory}
    if supports_resolver:
        kw["current_authority_resolver"] = current_authority_resolver
    guard = kcc.Guard.from_capsule(capsule, **kw)
    recorder = HostTraceRecorder(
        execution_id="revocation-run-001",
        capsule_id=capsule["capsule_id"],
        emitter_id=EMITTER,
        signing_key=PUBLIC_TEST_HMAC_KEY,
    )
    first = recorder.guarded_call(
        node_id="control", guard=guard, capability_id=cid, operation="update",
        parameters={"record_id": "synthetic-1", "value": "allowed"},
        dispatcher=dispatcher, now=101,
    )
    assert first["executed"] is True and len(calls) == 1

    denial_reasons = {}
    if supports_resolver:
        cases = [
            ("revoked", {"active": False, "reason": "reassigned"}),
            ("unknown", {"reason": "control_plane_unavailable"}),
            ("resolver_error", {"fault": True}),
        ]
        for node, update in cases:
            state.clear()
            state.update(update)
            try:
                recorder.guarded_call(
                    node_id=node, guard=guard, capability_id=cid,
                    operation="update",
                    parameters={"record_id": "synthetic-1", "value": node},
                    dispatcher=dispatcher, now=102,
                )
            except kcc.AuthorityDenied as exc:
                denial_reasons[node] = exc.reason
            else:
                raise AssertionError(f"{node} erroneously reached dispatcher")
        assert denial_reasons == {
            "revoked": "current_authority_revoked",
            "unknown": "current_authority_unknown",
            "resolver_error": "current_authority_resolver_error",
        }, denial_reasons
        assert len(resolver_calls) == 4
    assert len(calls) == 1
    bundle = recorder.finalize()
    verification = verify_host_bundle(
        bundle,
        signing_key=PUBLIC_TEST_HMAC_KEY,
        execution_id="revocation-run-001",
        capsule_id=capsule["capsule_id"],
        emitter_id=EMITTER,
    )
    assert verification["valid"] is True
    policy = {"version": "kcc.trajectory-policy.v0", "nodes": [
        {"id": "control", "kind": "dispatch", "capability_id": cid,
         "operation": "update", "after": []},
    ] + [
        {"id": node, "kind": "denial", "capability_id": cid,
         "operation": "update", "after": ["control"]}
        for node in denial_reasons
    ]}
    assert evaluate(policy, bundle["trace"])["pass"] is True
    return {
        "kcc_version": kcc.__version__,
        "synthetic_only": True,
        "version_feature_detected": supports_resolver,
        "current_authority_contract": (
            "verified_local_v0.2" if supports_resolver else
            "host_required_not_tested_on_stable"
        ),
        "authorized_dispatches": len(calls),
        "pre_dispatch_denials": len(denial_reasons),
        "denial_reasons": denial_reasons,
        "host_attestation_valid": True,
        "event_count": len(bundle["trace"]["events"]),
        "limitations": "Same-process PUBLIC test key; not a full-host security review, production approval or a live LLM test.",
    }


if __name__ == "__main__":
    print(json.dumps(run_drill(), sort_keys=True, indent=2))
