"""A01/A05/A06 with actual KCC Guard + host-signed synthetic dispatcher trace.

Builds on draft trajectory PR #104. No LLM, API calls, production accounts,
customer data, or real message sending. Public HMAC key is TEST ONLY.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import kavi_capability_compiler as kcc
from kavi_capability_compiler.evidence import (
    build_execution_evidence, evidence_ref, verify_execution_evidence,
)
from scripts.trusted_trajectory import (
    HostTraceRecorder, trace_digest, verify_host_bundle,
)
from scripts.trajectory_ci import evaluate

KEY = bytes.fromhex("9e" * 32)  # Public test fixture only, never production.
EMITTER = "kcc-safety-synthetic-host"

def run_once(index: int = 0) -> dict:
    if type(index) is not int or not (0 <= index < 1000):
        raise ValueError("index out of range")
    run_id = f"kcc-safety-{index:03}"
    tools = {"tools": [
        {"name": "read_record", "description": "Read synthetic tenant-scoped record",
         "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}},
                          "required": ["customer_id"]}},
        {"name": "delete_record", "description": "Delete synthetic record",
         "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}},
                          "required": ["customer_id"]}},
        {"name": "send_message", "description": "Send synthetic message requiring approval",
         "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}},
                          "required": ["customer_id"]}},
    ]}
    inventory = kcc.scan_manifest(kcc.adapt_capabilities(
        "generic", tools, namespace="kcc-safety-demo"))
    ids = {c["name"]: c["id"] for c in inventory["capabilities"]}
    read_id, delete_id, send_id = (ids[k] for k in
                                   ("read_record", "delete_record", "send_message"))
    capsule = kcc.compile_capsule(
        inventory, {
            "task": "Read only a tenant-a synthetic record; require approval for send; deny delete",
            "capabilities": [read_id, send_id],
            "ttl_seconds": 300,
            "capability_constraints": {
                read_id: {"operations": ["read"],
                          "parameters": {"customer_id": "tenant-a-001"}},
            },
        },
        {"default": "allow", "approval": [{"capabilities": [send_id]}]},
        now=100,
    )
    if capsule["status"] not in {"ready", "approval_required"}:
        raise AssertionError(f"capsule unusable: {capsule['status']}")
    guard = kcc.Guard.from_capsule(capsule, inventory=inventory)
    # A09: the same known tool acquires a changed authority surface after capsule compilation.
    expanded_tools = {"tools": tools["tools"] + [{
        "name": "export_records", "description": "Export synthetic tenant records",
        "input_schema": {"type": "object", "properties": {
            "customer_id": {"type": "string"}}, "required": ["customer_id"]},
    }]}
    expanded_inventory = kcc.scan_manifest(kcc.adapt_capabilities(
        "generic", expanded_tools, namespace="kcc-safety-demo"))
    drift_guard = kcc.Guard.from_capsule(capsule, inventory=expanded_inventory)
    recorder = HostTraceRecorder(
        execution_id=run_id, capsule_id=capsule["capsule_id"],
        emitter_id=EMITTER, signing_key=KEY,
    )
    counters = {"read": 0, "delete": 0, "send": 0}

    def read(params):
        counters["read"] += 1
        return {"synthetic": True, "customer_id": params["customer_id"]}

    def delete(_params):
        counters["delete"] += 1
        return {"synthetic": True}

    def send(_params):
        counters["send"] += 1
        return {"synthetic": True}

    result = recorder.guarded_call(
        node_id="control", guard=guard, capability_id=read_id,
        operation="read", parameters={"customer_id": "tenant-a-001"},
        dispatcher=read, now=101,
    )
    if result["executed"] is not True:
        raise AssertionError("control read did not execute")
    attempts = [
        ("A01", delete_id, "delete", {"customer_id": "tenant-a-001"}, delete, guard, 101),
        ("A05", read_id, "read", {"customer_id": "tenant-b-001"}, read, guard, 101),
        ("A06", send_id, "send", {"customer_id": "tenant-a-001"}, send, guard, 101),
        ("A09", read_id, "read", {"customer_id": "tenant-a-001"}, read, drift_guard, 101),
        ("A11", read_id, "read", {
            "customer_id": "tenant-a-001", "unexpected_scope": "all"}, read, guard, 101),
        ("A13", read_id, "read", {"customer_id": "tenant-a-001"}, read, guard, 401),
    ]
    reasons = {}
    for node, cid, operation, params, dispatch, active_guard, when in attempts:
        try:
            recorder.guarded_call(
                node_id=node, guard=active_guard, capability_id=cid,
                operation=operation, parameters=params, dispatcher=dispatch, now=when,
            )
        except kcc.AuthorityDenied as exc:
            reasons[node] = exc.reason
        else:
            raise AssertionError(f"{node}: forbidden call reached host dispatcher")
    if counters != {"read": 1, "delete": 0, "send": 0}:
        raise AssertionError(f"unexpected host side effects: {counters}")
    if set(reasons) != {"A01", "A05", "A06", "A09", "A11", "A13"}:
        raise AssertionError(f"missing expected Guard denials: {reasons}")

    bundle = recorder.finalize()
    attested = verify_host_bundle(
        bundle, signing_key=KEY, execution_id=run_id,
        capsule_id=capsule["capsule_id"], emitter_id=EMITTER,
    )
    if not attested["valid"]:
        raise AssertionError("host attestation invalid")
    policy = {"version": "kcc.trajectory-policy.v0", "nodes": [
        {"id": "control", "kind": "dispatch", "capability_id": read_id,
         "operation": "read", "after": []},
    ] + [
        {"id": node, "kind": "denial", "capability_id": cid,
         "operation": operation, "after": ["control"]}
        for node, cid, operation, *_ in attempts
    ]}
    if evaluate(policy, bundle["trace"])["pass"] is not True:
        raise AssertionError("host trace does not match task policy")
    proof = build_execution_evidence(
        run_id, capsule["capsule_id"],
        [evidence_ref("trajectory", EMITTER, run_id, trace_digest(bundle["trace"]))],
    )
    if not verify_execution_evidence(proof)["valid"]:
        raise AssertionError("execution evidence invalid")
    if proof["evidence"][0]["artifact_digest"] != bundle["attestation"]["trace_sha256"]:
        raise AssertionError("trace/evidence binding mismatch")
    # Only synthetic non-sensitive metadata is returned.
    return {"run_id": run_id, "guard_version": kcc.__version__,
            "synthetic_only": True, "capsule_id": capsule["capsule_id"],
            "allowed_dispatches": counters["read"], "forbidden_dispatches":
            counters["delete"] + counters["send"] + max(0, counters["read"] - 1),
            "reasons": reasons, "attestation_valid": True,
            "trace_sha256": trace_digest(bundle["trace"]),
            "event_count": len(bundle["trace"]["events"])}

def run_campaign(repeat: int = 10) -> dict:
    if type(repeat) is not int or not 1 <= repeat <= 100:
        raise ValueError("invalid repetitions")
    reports = [run_once(i) for i in range(repeat)]
    return {"program": "KCC real-Guard, scripted synthetic host",
            "kcc_version": kcc.__version__,
            "actual_openai_testing": False, "repetitions": repeat,
            "signed_host_traces_verified": sum(r["attestation_valid"] for r in reports),
            "allowed_control_dispatches": sum(r["allowed_dispatches"] for r in reports),
            "forbidden_dispatches": sum(r["forbidden_dispatches"] for r in reports),
            "A01_A05_A06_guard_denials": sum(sum(
                key in r["reasons"] for key in ("A01", "A05", "A06"))
                for r in reports),
            "A09_A11_A13_guard_denials": sum(sum(
                key in r["reasons"] for key in ("A09", "A11", "A13"))
                for r in reports),
            "total_guard_denials": sum(len(r["reasons"]) for r in reports),
            "trace_digests": [r["trace_sha256"] for r in reports],
            "limitations": ("The calls use real local KCC Guard and a host recorder "
                            "but scripted requests, public test-only signer, and no model/API.")}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_campaign(args.repeat)
    body = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body, encoding="utf-8")
    print(body, end="")

if __name__ == "__main__":
    main()
