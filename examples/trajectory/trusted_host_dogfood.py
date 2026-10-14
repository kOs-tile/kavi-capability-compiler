"""Real KCC Guard + synthetic data + host-produced, non-self-attested trace.

No network, real CRM, message sending, external credentials or Hermes actions.
Use: python -m examples.trajectory.trusted_host_dogfood --output /tmp/trace.json
       --policy-output /tmp/policy.json --evidence-output /tmp/evidence.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import kavi_capability_compiler as kcc
from kavi_capability_compiler.evidence import (
    build_execution_evidence, evidence_ref, verify_execution_evidence,
)
from scripts.trusted_trajectory import HostTraceRecorder, trace_digest, verify_host_bundle
from scripts.trajectory_ci import evaluate

RUN_ID = "synthetic-run-001"
EMITTER = "kcc-synthetic-host"
KEY_HEX = "1b" * 32  # PUBLIC TEST KEY. Never use for a real production host.


def dogfood() -> tuple[dict, dict, dict]:
    tool_defs = {"tools": [
        {"name": "read_customer", "description": "Read a synthetic customer record",
         "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}},
                          "required": ["customer_id"]}},
        {"name": "delete_customer", "description": "Delete a customer record",
         "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}},
                          "required": ["customer_id"]}},
        {"name": "send_message", "description": "Send a message",
         "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}},
                          "required": ["customer_id"]}},
    ]}
    inventory = kcc.scan_manifest(kcc.adapt_capabilities(
        "generic", tool_defs, namespace="trajectory-dogfood"))
    ids = {c["name"]: c["id"] for c in inventory["capabilities"]}
    read_id, delete_id, send_id = (ids[name] for name in
                                   ("read_customer", "delete_customer", "send_message"))
    capsule = kcc.compile_capsule(inventory, {
        "task": "Read one synthetic customer, request message approval; no deletion",
        "capabilities": [read_id, send_id],
        "ttl_seconds": 300,
        "capability_constraints": {read_id: {
            "operations": ["read"], "parameters": {"customer_id": "synthetic-001"}}},
    }, {"default": "allow", "approval": [{"capabilities": [send_id]}]}, now=100)
    guard = kcc.Guard.from_capsule(capsule, inventory=inventory)
    assert guard.capsule_id == capsule["capsule_id"]
    recorder = HostTraceRecorder(execution_id=RUN_ID, capsule_id=capsule["capsule_id"],
                                 emitter_id=EMITTER, signing_key=bytes.fromhex(KEY_HEX))
    counts = {"read": 0, "delete": 0, "send": 0}

    def read(params):
        counts["read"] += 1
        return {"customer_id": params["customer_id"], "synthetic": True}

    def delete(_params):
        counts["delete"] += 1
        return {"deleted": True}

    def send(_params):
        counts["send"] += 1
        return {"sent": True}

    result = recorder.guarded_call(node_id="read", guard=guard,
                                   capability_id=read_id, operation="read",
                                   parameters={"customer_id": "synthetic-001"},
                                   dispatcher=read, now=101)
    assert result["executed"] is True
    reasons = {}
    for node_id, cid, operation, dispatcher in (
        ("deny_delete", delete_id, "delete", delete),
        ("approval_handoff", send_id, "send", send),
    ):
        try:
            recorder.guarded_call(node_id=node_id, guard=guard,
                                  capability_id=cid, operation=operation,
                                  parameters={"customer_id": "synthetic-001"},
                                  dispatcher=dispatcher, now=101)
        except kcc.AuthorityDenied as exc:
            reasons[node_id] = exc.reason
        else:
            raise AssertionError(f"{node_id}: unauthorized call reached dispatcher")
    assert reasons == {"deny_delete": "capability_not_granted",
                       "approval_handoff": "approval_required"}, reasons
    assert counts == {"read": 1, "delete": 0, "send": 0}, counts

    bundle = recorder.finalize()
    verify_host_bundle(bundle, signing_key=bytes.fromhex(KEY_HEX),
                       execution_id=RUN_ID, capsule_id=capsule["capsule_id"], emitter_id=EMITTER)
    policy = {"version": "kcc.trajectory-policy.v0", "nodes": [
        {"id": "read", "kind": "dispatch", "capability_id": read_id,
         "operation": "read", "after": []},
        {"id": "deny_delete", "kind": "denial", "capability_id": delete_id,
         "operation": "delete", "after": ["read"]},
        {"id": "approval_handoff", "kind": "denial", "capability_id": send_id,
         "operation": "send", "after": ["read"]},
    ]}
    assert evaluate(policy, bundle["trace"])["pass"] is True
    bound = build_execution_evidence(
        RUN_ID, capsule["capsule_id"],
        [evidence_ref("trajectory", EMITTER, RUN_ID, trace_digest(bundle["trace"]))])
    assert verify_execution_evidence(bound)["valid"] is True
    assert bound["evidence"][0]["artifact_digest"] == bundle["attestation"]["trace_sha256"]
    summary = {"pass": True, "synthetic_only": True, "dispatches": counts,
               "denial_reasons": reasons, "execution_id": RUN_ID,
               "emitter_id": EMITTER, "capsule_id": capsule["capsule_id"],
               "trace_sha256": trace_digest(bundle["trace"]),
               "bound_evidence_digest": bound["digest"]}
    return bundle, policy, {"evidence": bound, "summary": summary}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--policy-output", required=True, type=Path)
    parser.add_argument("--evidence-output", required=True, type=Path)
    args = parser.parse_args()
    bundle, policy, evidence = dogfood()
    for path, payload in ((args.output, bundle), (args.policy_output, policy),
                          (args.evidence_output, evidence)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print("KCC_TRUSTED_TRAJECTORY_DOGFOOD: PASS")
    print("SUMMARY_JSON=" + json.dumps(evidence["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
