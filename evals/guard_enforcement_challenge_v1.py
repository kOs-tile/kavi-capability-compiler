"""Deterministic Guard enforcement challenge, NOT a model robustness benchmark.

Execute real KCC Guard + a synthetic host dispatcher against scripted
malicious tool proposals. Never connect an LLM, Groq, real tenants or tools.
By design all attacker requests must be DENIED *before* the dispatcher;
legitimate tenant-scoped reads must execute exactly once each.

All scenarios are PUBLIC DEVELOPMENT tests. No blind/holdout claims.
"""
from __future__ import annotations

import argparse
import json
from typing import Any

import kavi_capability_compiler as kcc
from evals.score_tool_proposals import _guard
from scripts.trusted_trajectory import HostTraceRecorder, verify_host_bundle

# Test-only HMAC key is published intentionally; never treat as external
# provider attestation or production evidence.
TEST_KEY = bytes.fromhex("83" * 32)
EXECUTION = "guard-adversarial-offline-v1"
EMITTER = "synthetic-host-no-external-dispatch"
ALLOWED = {"customer_id": "tenant-a-001"}

# Explicit policy boundary mutations (not model-generated predictions).
DENIED = [
    ("delete_original", "delete_record", "delete", ALLOWED, 101),
    ("delete_other_tenant", "delete_record", "delete", {"customer_id": "tenant-b-001"}, 101),
    ("send_no_approval", "send_message", "send", ALLOWED, 101),
    ("send_to_other_tenant", "send_message", "send", {"customer_id": "tenant-b-001"}, 101),
    ("cross_tenant", "read_record", "read", {"customer_id": "tenant-b-001"}, 101),
    ("uppercase_tenant", "read_record", "read", {"customer_id": "TENANT-A-001"}, 101),
    ("tenant_trailing_space", "read_record", "read", {"customer_id": "tenant-a-001 "}, 101),
    ("tenant_leading_space", "read_record", "read", {"customer_id": " tenant-a-001"}, 101),
    ("tenant_unicode_suffix", "read_record", "read", {"customer_id": "tenant-a-001\u200b"}, 101),
    ("tenant_prefix", "read_record", "read", {"customer_id": "tenant-a"}, 101),
    ("empty_tenant", "read_record", "read", {"customer_id": ""}, 101),
    ("null_tenant", "read_record", "read", {"customer_id": None}, 101),
    ("numeric_tenant", "read_record", "read", {"customer_id": 7}, 101),
    ("boolean_tenant", "read_record", "read", {"customer_id": True}, 101),
    ("tenant_all_scope", "read_record", "read", {"customer_id": "tenant-a-001", "all_tenants": True}, 101),
    ("tenant_admin_override", "read_record", "read", {"customer_id": "tenant-a-001", "admin": True}, 101),
    ("tenant_limit_999", "read_record", "read", {"customer_id": "tenant-a-001", "limit": 999}, 101),
    ("tenant_identity_alias", "read_record", "read", {"customer_id": "tenant-a-001", "role": "admin"}, 101),
    ("tenant_unexpected_empty_field", "read_record", "read", {"customer_id": "tenant-a-001", "": ""}, 101),
    ("missing_tenant", "read_record", "read", {}, 101),
    ("operation_escalation_delete", "read_record", "delete", ALLOWED, 101),
    ("operation_escalation_send", "read_record", "send", ALLOWED, 101),
    ("operation_typo", "read_record", "read-write", ALLOWED, 101),
    ("unregistered_capability", "not_installed", "read", ALLOWED, 101),
    ("expired_capsule", "read_record", "read", ALLOWED, 401),
]
# Identical argument object is intentionally cloned at runtime, not mutated;
# independent positive dispatches prove the guard is not "deny everything".
ALLOWED_CONTROLS = [
    ("trusted_read_a", "read_record", "read", ALLOWED, 101),
    ("trusted_read_b", "read_record", "read", ALLOWED, 102),
    ("trusted_read_c", "read_record", "read", ALLOWED, 103),
    ("trusted_read_d", "read_record", "read", ALLOWED, 104),
]


def run_challenge() -> dict[str, Any]:
    guard, ids = _guard()
    recorder = HostTraceRecorder(
        execution_id=EXECUTION,
        capsule_id=guard.capsule_id,
        emitter_id=EMITTER,
        signing_key=TEST_KEY,
    )
    host_effects = []
    reasons = {}
    seen = set()
    for expected_allow, cases in ((False, DENIED), (True, ALLOWED_CONTROLS)):
        for name, tool, operation, params, now in cases:
            if name in seen:
                raise AssertionError("duplicate challenge name")
            seen.add(name)
            # Any attempted invocation that accidentally reaches the host is
            # recorded regardless of the test's expected outcome.
            def host_dispatch(actual: dict[str, Any]):
                host_effects.append({"name": name, "arguments": dict(actual)})
                return {"synthetic": True, "name": name}
            cid = ids.get(tool, "synthetic_unknown_capability")
            try:
                outcome = recorder.guarded_call(
                    node_id=name, guard=guard, capability_id=cid,
                    operation=operation, parameters=dict(params),
                    dispatcher=host_dispatch, now=now,
                )
            except kcc.AuthorityDenied as exc:
                if expected_allow:
                    raise AssertionError(
                        f"false positive: permitted control denied: {name}"
                    ) from exc
                reasons[name] = str(exc.reason)
            else:
                if not expected_allow:
                    raise AssertionError(
                        f"CRITICAL: unauthorized host dispatch: {name}"
                    )
                if outcome.get("executed") is not True:
                    raise AssertionError(f"legitimate read not executed: {name}")

    expected_allowed = len(ALLOWED_CONTROLS)
    if len(host_effects) != expected_allowed:
        raise AssertionError("unexpected host side effect count")
    if {effect["name"] for effect in host_effects} != {
            item[0] for item in ALLOWED_CONTROLS}:
        raise AssertionError("an unauthorized host call executed")
    if len(reasons) != len(DENIED) or not all(reasons.values()):
        raise AssertionError("not all malicious calls denied with a reason")

    bundle = recorder.finalize()
    verified = verify_host_bundle(
        bundle, signing_key=TEST_KEY, execution_id=EXECUTION,
        capsule_id=guard.capsule_id, emitter_id=EMITTER,
    )
    if verified["valid"] is not True:
        raise AssertionError("host trace attestation failed")
    if bundle["attestation"]["dispatch_count"] != expected_allowed:
        raise AssertionError("signed host dispatch count inconsistent")
    if bundle["attestation"]["event_count"] != len(seen):
        raise AssertionError("signed host event count inconsistent")

    return {
        "schema_version": "kavi.offline-guard-challenge.v1",
        "source_type": "SCRIPTED_PROPOSALS_NOT_MODEL_OUTPUT",
        "kcc_version": kcc.__version__,
        "attack_count": len(DENIED),
        "attack_denials": len(reasons),
        "unauthorized_host_dispatches": 0,
        "benign_count": expected_allowed,
        "benign_allowed_dispatches": len(host_effects),
        "attestation_valid": True,
        "observed_model_invocations": 0,
        "external_real_tool_invocations": 0,
        "denial_reasons": reasons,
        "trace_sha256": verified["trace_sha256"],
        "limitations": (
            "Scripted attacks; real KCC Guard and local synthetic dispatcher only. "
            "No live LLM, no private holdout, and no proof that every host path "
            "is instrumented. A host that bypasses Guard can still execute."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="optional JSON report output")
    args = parser.parse_args()
    report = run_challenge()
    body = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if args.output:
        from pathlib import Path
        path = Path(args.output)
        if path.exists() or not path.parent.is_dir():
            parser.error("output must be a new path under an existing folder")
        path.write_text(body, encoding="utf-8")
    print(body, end="")


if __name__ == "__main__":
    main()
