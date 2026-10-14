"""Isolated actual KCC Guard + HMAC approval + durable SQLite journal dogfood.

No real messages, no Hermes connection, no network. Public keys here are
deliberately TEST-ONLY and confer no real human authority.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import kavi_capability_compiler as kcc
from kavi_capability_compiler.evidence import (
    build_execution_evidence, evidence_ref, verify_execution_evidence,
)
from scripts.approval_and_journal import (
    DurableDispatchJournal, InvalidArtifact, issue_test_receipt,
)
from scripts.trusted_trajectory import (
    HostTraceRecorder, trace_digest, verify_host_bundle,
)
from scripts.trajectory_ci import evaluate

RUN = "synthetic-approved-run-001"
EMITTER = "kcc-synthetic-approved-host"
ACTOR = "founder-test"
APPROVAL_KEY = bytes.fromhex("ab" * 32)  # PUBLIC TEST KEY
TRACE_KEY = bytes.fromhex("cd" * 32)     # PUBLIC TEST KEY


def run_dogfood(storage_dir: Path) -> tuple[dict, dict, dict]:
    tools = {"tools": [{
        "name": "send_message", "description": "Send a synthetic-only demo message",
        "input_schema": {"type": "object",
                         "properties": {"customer_id": {"type": "string"}},
                         "required": ["customer_id"]},
    }]}
    manifest = kcc.adapt_capabilities("generic", tools, namespace="durable-host-demo")
    inventory = kcc.scan_manifest(manifest)
    cid = inventory["capabilities"][0]["id"]
    capsule = kcc.compile_capsule(
        inventory, {"task": "Send one synthetic approved message", "capabilities": [cid],
                    "ttl_seconds": 300,
                    "capability_constraints": {cid: {
                        "operations": ["send"],
                        "parameters": {"customer_id": "synthetic-customer"}}},
        }, {"default": "allow"}, now=100)
    assert capsule["status"] == "ready", capsule["status"]
    guard = kcc.Guard.from_capsule(capsule, inventory=inventory)
    policy = {"version": "kcc.trajectory-policy.v0", "nodes": [
        {"id": "approve", "kind": "approval", "capability_id": cid,
         "operation": "send", "after": []},
        {"id": "send", "kind": "dispatch", "capability_id": cid,
         "operation": "send", "after": ["approve"]},
    ]}
    storage_dir.mkdir(parents=True, exist_ok=True)
    journal_path = storage_dir / "journal.sqlite3"
    calls = []
    journal = DurableDispatchJournal(
        journal_path, approval_required=frozenset({(cid, "send")}))
    recorder = HostTraceRecorder(
        execution_id=RUN, capsule_id=capsule["capsule_id"],
        emitter_id=EMITTER, signing_key=TRACE_KEY)
    params = {"customer_id": "synthetic-customer"}

    def fake_host_send(arguments):
        calls.append(dict(arguments))
        return {"delivered": True, "synthetic": True}

    try:
        journal.run_once(execution_id=RUN, capsule_id=capsule["capsule_id"],
                         step_id="send", capability_id=cid, operation="send",
                         parameters=params, guard=guard, dispatcher=fake_host_send, now=101,
                         recorder=recorder)
        raise AssertionError("missing approval must fail")
    except InvalidArtifact:
        assert calls == []

    approved = issue_test_receipt(
        key=APPROVAL_KEY, execution_id=RUN, capsule_id=capsule["capsule_id"],
        step_id="send", capability_id=cid, operation="send",
        actor_id=ACTOR, now=100, ttl=30)
    common = dict(execution_id=RUN, capsule_id=capsule["capsule_id"],
                  step_id="send", capability_id=cid, operation="send",
                  parameters=params, guard=guard, now=101,
                  approval_receipt=approved, approval_key=APPROVAL_KEY,
                  expected_approver=ACTOR, approval_node_id="approve")
    first = journal.run_once(**common, recorder=recorder,
                             dispatcher=fake_host_send)
    assert first["state"] == "completed"
    assert calls == [params]
    bundle = recorder.finalize()
    assert evaluate(policy, bundle["trace"])["pass"] is True
    assert verify_host_bundle(
        bundle, signing_key=TRACE_KEY, execution_id=RUN,
        capsule_id=capsule["capsule_id"], emitter_id=EMITTER)["valid"]
    journal.close()

    journal = DurableDispatchJournal(
        journal_path, approval_required=frozenset({(cid, "send")}))
    replay = journal.run_once(
        **common, recorder=HostTraceRecorder(
            execution_id=RUN, capsule_id=capsule["capsule_id"],
            emitter_id=EMITTER, signing_key=TRACE_KEY),
        dispatcher=lambda p: (_ for _ in ()).throw(AssertionError("double send")))
    journal.close()
    assert replay["state"] == "already_completed" and len(calls) == 1

    proof = build_execution_evidence(
        RUN, capsule["capsule_id"],
        [evidence_ref("trajectory", EMITTER, RUN, trace_digest(bundle["trace"]))])
    assert verify_execution_evidence(proof)["valid"] is True
    assert proof["evidence"][0]["artifact_digest"] == bundle["attestation"]["trace_sha256"]
    report = {"status": "PASS", "synthetic_only": True,
              "execution_id": RUN, "emitter_id": EMITTER,
              "capsule_id": capsule["capsule_id"], "capability_id": cid,
              "approved_dispatches": len(calls), "denied_without_receipt": True,
              "restart_replay_blocked": True,
              "trace_sha256": bundle["attestation"]["trace_sha256"],
              "evidence_digest": proof["digest"]}
    return bundle, policy, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    bundle, policy, report = run_dogfood(args.output_dir)
    for name, data in (("bundle.json", bundle), ("policy.json", policy),
                       ("report.json", report)):
        (args.output_dir / name).write_text(
            json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("KCC_APPROVED_DURABLE_DOGFOOD: PASS")
    print("REPORT_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
