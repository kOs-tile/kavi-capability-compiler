"""Host-emitted trace regression tests; synthetic only, no external tools."""
import copy
import json
import subprocess
import sys

import pytest
from kavi_capability_compiler.runtime import AuthorityDenied
from scripts.trusted_trajectory import (
    HostTraceRecorder, InvalidArtifact, trace_digest, verify_host_bundle,
)
from scripts.trajectory_ci import evaluate
from examples.trajectory.trusted_host_dogfood import dogfood

KEY = bytes.fromhex("1b" * 32)  # PUBLIC fixture key; never production.
CAPSULE = "a" * 64
RUN = "test-run-1"
EMITTER = "test-host"


class FakeGuard:
    capsule_id = CAPSULE

    def dispatch_sync(self, cid, fn, *, operation, parameters, now=None):
        if cid == "denied-tool":
            raise AuthorityDenied({"allowed": False, "reason": "capability_not_granted"})
        return {"executed": True, "result": fn(parameters)}


def recorder():
    return HostTraceRecorder(execution_id=RUN, capsule_id=CAPSULE,
                             emitter_id=EMITTER, signing_key=KEY)


def observed_bundle():
    rec = recorder()
    hits = []
    rec.guarded_call(node_id="read", guard=FakeGuard(), capability_id="read-tool",
                     operation="read", parameters={"customer_id": "synthetic"},
                     dispatcher=lambda p: hits.append(dict(p)) or "OK")
    with pytest.raises(AuthorityDenied):
        rec.guarded_call(node_id="denied", guard=FakeGuard(), capability_id="denied-tool",
                         operation="delete", parameters={"customer_id": "synthetic"},
                         dispatcher=lambda p: (_ for _ in ()).throw(AssertionError("called")))
    assert hits == [{"customer_id": "synthetic"}]
    return rec.finalize()


def verify(bundle):
    return verify_host_bundle(bundle, signing_key=KEY, execution_id=RUN,
                              capsule_id=CAPSULE, emitter_id=EMITTER)


def policy():
    return {"version": "kcc.trajectory-policy.v0", "nodes": [
        {"id": "read", "kind": "dispatch", "capability_id": "read-tool",
         "operation": "read", "after": []},
        {"id": "denied", "kind": "denial", "capability_id": "denied-tool",
         "operation": "delete", "after": ["read"]},
    ]}


def test_host_emits_completed_dispatch_and_guard_denial():
    b = observed_bundle()
    assert verify(b)["valid"]
    assert b["attestation"]["dispatch_count"] == 1
    assert evaluate(policy(), b["trace"])["pass"]
    assert b["trace"]["events"][1]["outcome"] == "denied"
    assert "customer_id" not in json.dumps(b)


def test_real_kcc_guard_dogfood_and_evidence_binding():
    b, p, proof = dogfood()
    assert evaluate(p, b["trace"])["pass"]
    assert proof["summary"]["dispatches"] == {"read": 1, "delete": 0, "send": 0}
    assert proof["summary"]["denial_reasons"]["approval_handoff"] == "approval_required"
    assert proof["evidence"]["evidence"][0]["artifact_digest"] == trace_digest(b["trace"])


def test_tampered_trace_rejected():
    b = observed_bundle()
    b["trace"]["events"][0]["operation"] = "delete"
    with pytest.raises(InvalidArtifact, match="digest"):
        verify(b)


def test_forged_approval_event_rejected():
    b = observed_bundle()
    b["trace"]["events"][1] = dict(b["trace"]["events"][1], kind="approval",
                                  outcome="approved")
    b["attestation"]["trace_sha256"] = trace_digest(b["trace"])
    with pytest.raises(InvalidArtifact, match="MAC|mac|counts"):
        verify(b)


def test_cross_run_capsule_emitter_replay_rejected():
    b = observed_bundle()
    for override in ({"execution_id": "other-run"}, {"capsule_id": "b" * 64},
                     {"emitter_id": "other-host"}):
        identity = dict(execution_id=RUN, capsule_id=CAPSULE, emitter_id=EMITTER)
        identity.update(override)
        with pytest.raises(InvalidArtifact, match="mismatch"):
            verify_host_bundle(b, signing_key=KEY, **identity)


def test_wrong_key_rejected():
    b = observed_bundle()
    with pytest.raises(InvalidArtifact, match="MAC"):
        verify_host_bundle(b, signing_key=b"2" * 32,
                           execution_id=RUN, capsule_id=CAPSULE, emitter_id=EMITTER)


def test_dispatch_failure_never_finalizes():
    rec = recorder()
    def failing(_):
        raise RuntimeError("host failure")
    with pytest.raises(RuntimeError, match="host failure"):
        rec.guarded_call(node_id="read", guard=FakeGuard(), capability_id="read-tool",
                         operation="read", parameters={}, dispatcher=failing)
    with pytest.raises(InvalidArtifact, match="failed"):
        rec.finalize()


def test_dispatcher_forged_authority_denial_not_guard_denial():
    rec = recorder()
    def failing(_):
        raise AuthorityDenied({"reason": "pretend_guard_denial"})
    with pytest.raises(AuthorityDenied):
        rec.guarded_call(node_id="read", guard=FakeGuard(), capability_id="read-tool",
                         operation="read", parameters={}, dispatcher=failing)
    with pytest.raises(InvalidArtifact):
        rec.finalize()


def test_wrong_guard_capsule_rejected():
    rec = recorder()
    guard = FakeGuard()
    guard.capsule_id = "b" * 64
    with pytest.raises(InvalidArtifact, match="capsule"):
        rec.guarded_call(node_id="read", guard=guard, capability_id="read-tool",
                         operation="read", parameters={}, dispatcher=lambda _: None)


def test_closed_session_rejects_new_events():
    rec = recorder()
    rec.guarded_call(node_id="read", guard=FakeGuard(), capability_id="read-tool",
                     operation="read", parameters={}, dispatcher=lambda _: None)
    rec.finalize()
    with pytest.raises(InvalidArtifact):
        rec.guarded_call(node_id="later", guard=FakeGuard(), capability_id="read-tool",
                         operation="read", parameters={}, dispatcher=lambda _: None)


def test_missing_event_never_passes_even_when_trace_regenerated():
    b = observed_bundle()
    truncated = copy.deepcopy(b["trace"])
    truncated["events"].pop(1)
    assert evaluate(policy(), truncated)["pass"] is False


def test_cli_requires_key_and_verifies_exact_run(tmp_path, monkeypatch):
    b = observed_bundle()
    (tmp_path / "bundle.json").write_text(json.dumps(b))
    (tmp_path / "policy.json").write_text(json.dumps(policy()))
    args = [sys.executable, "-m", "scripts.trusted_trajectory",
            "--policy", str(tmp_path / "policy.json"), "--bundle", str(tmp_path / "bundle.json"),
            "--execution-id", RUN, "--capsule-id", CAPSULE, "--emitter-id", EMITTER]
    monkeypatch.delenv("KCC_TRACE_ATTEST_KEY_HEX", raising=False)
    bad = subprocess.run(args, capture_output=True, text=True)
    assert bad.returncode == 2
    monkeypatch.setenv("KCC_TRACE_ATTEST_KEY_HEX", KEY.hex())
    good = subprocess.run(args, capture_output=True, text=True)
    assert good.returncode == 0, good.stderr + good.stdout
