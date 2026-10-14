"""Host-owned approval and SQLite retry regression. Synthetic data only."""
import json

import pytest
from kavi_capability_compiler.runtime import AuthorityDenied
from scripts.approval_and_journal import (
    DurableDispatchJournal, AmbiguousOutcome, JournalConflict,
    issue_test_receipt, verify_receipt, InvalidArtifact,
)
from scripts.trusted_trajectory import HostTraceRecorder, verify_host_bundle
from scripts.trajectory_ci import evaluate

CAPSULE = "a" * 64
KEY = b"a" * 32  # public test key
ATTEST = b"t" * 32  # public test key
RUN = "run-001"
EMITTER = "host-001"


class FakeGuard:
    capsule_id = CAPSULE

    def dispatch_sync(self, cid, fn, *, operation, parameters, now=None):
        if cid == "delete":
            raise AuthorityDenied({"reason": "capability_not_granted", "allowed": False})
        return {"executed": True, "result": fn(parameters)}


def receipt(**overrides):
    kwargs = dict(key=KEY, execution_id=RUN, capsule_id=CAPSULE, step_id="send",
                  capability_id="message", operation="send", actor_id="founder",
                  now=100, ttl=30)
    kwargs.update(overrides)
    return issue_test_receipt(**kwargs)


def record():
    return HostTraceRecorder(execution_id=RUN, capsule_id=CAPSULE,
                             emitter_id=EMITTER, signing_key=ATTEST)


def execute(journal, recorder=None, step_id="send", approval=True, fn=None):
    return journal.run_once(
        execution_id=RUN, capsule_id=CAPSULE, step_id=step_id,
        capability_id="message", operation="send", parameters={"synthetic": True},
        guard=FakeGuard(), dispatcher=fn or (lambda p: {"delivered": True}),
        now=101, recorder=recorder,
        approval_receipt=receipt() if approval else None,
        approval_key=KEY if approval else None,
        expected_approver="founder" if approval else None,
        approval_node_id="approve" if approval else None,
    )


def test_signed_receipt():
    verify_receipt(receipt(), key=KEY, execution_id=RUN, capsule_id=CAPSULE,
                   step_id="send", capability_id="message", operation="send",
                   actor_id="founder", now=101)


@pytest.mark.parametrize("changed", [
    {"step_id": "other"}, {"capsule_id": "b" * 64},
    {"actor_id": "unknown"}, {"decision": "denied"},
    {"operation": "delete"}, {"issued_at": 200}, {"expires_at": 100},
    {"mac_sha256": "0" * 64},
])
def test_tampered_or_mismatched_receipts_fail_closed(changed):
    r = receipt()
    r.update(changed)
    with pytest.raises(InvalidArtifact):
        verify_receipt(r, key=KEY, execution_id=RUN, capsule_id=CAPSULE,
                       step_id="send", capability_id="message", operation="send",
                       actor_id="founder", now=101)


def test_host_approved_dispatch_then_restart_no_duplicate(tmp_path):
    path = tmp_path / "journal.db"
    journal = DurableDispatchJournal(path, approval_required=frozenset({("message", "send")}))
    hits = []
    rec = record()
    first = execute(journal, recorder=rec,
                    fn=lambda p: hits.append(dict(p)) or {"delivered": True})
    assert first["state"] == "completed" and len(hits) == 1
    policy = {"version": "kcc.trajectory-policy.v0", "nodes": [
        {"id": "approve", "kind": "approval", "capability_id": "message",
         "operation": "send", "after": []},
        {"id": "send", "kind": "dispatch", "capability_id": "message",
         "operation": "send", "after": ["approve"]},
    ]}
    bundle = rec.finalize()
    assert evaluate(policy, bundle["trace"])["pass"]
    assert bundle["attestation"]["dispatch_count"] == 1
    assert verify_host_bundle(bundle, signing_key=ATTEST, execution_id=RUN,
                              capsule_id=CAPSULE, emitter_id=EMITTER)["valid"]
    assert "synthetic" not in json.dumps(bundle)
    journal.close()
    journal = DurableDispatchJournal(path, approval_required=frozenset({("message", "send")}))
    again = execute(journal, recorder=record(),
                    fn=lambda p: hits.append(dict(p)))
    assert again["state"] == "already_completed"
    assert len(hits) == 1
    journal.close()


def test_host_policy_requires_approval_before_any_dispatch(tmp_path):
    journal = DurableDispatchJournal(tmp_path / "j.db",
                                     approval_required=frozenset({("message", "send")}))
    hits = []
    with pytest.raises(InvalidArtifact, match="requires signed approval"):
        execute(journal, approval=False, fn=lambda p: hits.append(p))
    assert hits == []


def test_unknown_effect_after_crash_never_auto_retries(tmp_path):
    path = tmp_path / "j.db"
    journal = DurableDispatchJournal(path)
    def uncertain(_):
        raise RuntimeError("remote timeout after side effect")
    with pytest.raises(RuntimeError):
        execute(journal, recorder=record(), fn=uncertain)
    journal.close()
    journal = DurableDispatchJournal(path)
    with pytest.raises(AmbiguousOutcome, match="reconcile"):
        execute(journal, recorder=record(),
                fn=lambda p: pytest.fail("duplicate external side effect"))


def test_conflicting_step_reuse_blocked(tmp_path):
    path = tmp_path / "j.db"
    journal = DurableDispatchJournal(path)
    execute(journal, recorder=record())
    journal.close()
    journal = DurableDispatchJournal(path)
    with pytest.raises(JournalConflict):
        journal.run_once(
            execution_id=RUN, capsule_id=CAPSULE, step_id="send",
            capability_id="message", operation="send", parameters={"changed": 1},
            guard=FakeGuard(), dispatcher=lambda _: None, now=101)


def test_receipt_cannot_be_replayed_into_new_step(tmp_path):
    journal = DurableDispatchJournal(tmp_path / "j.db")
    with pytest.raises(InvalidArtifact, match="mismatch"):
        execute(journal, recorder=record(), step_id="other")


def test_guard_denial_dispatches_zero_times_and_is_not_retried(tmp_path):
    journal = DurableDispatchJournal(tmp_path / "j.db")
    hits = []
    opts = dict(execution_id=RUN, capsule_id=CAPSULE, step_id="delete",
                capability_id="delete", operation="delete", parameters={},
                guard=FakeGuard(), now=101, recorder=record())
    with pytest.raises(AuthorityDenied):
        journal.run_once(**opts, dispatcher=lambda p: hits.append(p))
    assert hits == []
    with pytest.raises(JournalConflict):
        journal.run_once(**opts, dispatcher=lambda p: pytest.fail("executed"))


def test_forged_approval_does_not_reach_dispatcher(tmp_path):
    journal = DurableDispatchJournal(tmp_path / "j.db")
    bad = receipt()
    bad["actor_id"] = "spoofed"
    with pytest.raises(InvalidArtifact):
        journal.run_once(
            execution_id=RUN, capsule_id=CAPSULE, step_id="send",
            capability_id="message", operation="send", parameters={},
            guard=FakeGuard(), dispatcher=lambda _: pytest.fail("executed"), now=101,
            recorder=record(), approval_receipt=bad,
            approval_key=KEY, expected_approver="founder",
            approval_node_id="approve")


def test_process_crash_after_dispatch_is_not_blindly_retried(tmp_path):
    """Child exits without recording completion; parent must reconcile first."""
    import os
    import subprocess
    import sys

    db_path = tmp_path / "crashed-run.sqlite3"
    child = r'''
import os
from scripts.approval_and_journal import DurableDispatchJournal
class Guard:
    capsule_id = "a" * 64
    def dispatch_sync(self, cid, fn, *, operation, parameters, now=None):
        return {"executed": True, "result": fn(parameters)}
journal = DurableDispatchJournal(os.environ["KCC_CRASH_DB"])
journal.run_once(
    execution_id="run-001", capsule_id="a"*64, step_id="send",
    capability_id="message", operation="send", parameters={"synthetic": True},
    guard=Guard(), now=101, dispatcher=lambda p: os._exit(14))
'''
    env = dict(os.environ, KCC_CRASH_DB=str(db_path))
    proc = subprocess.run([sys.executable, "-c", child],
                          env=env, capture_output=True, text=True, timeout=15)
    assert proc.returncode == 14, proc.stderr + proc.stdout
    journal = DurableDispatchJournal(db_path)
    with pytest.raises(AmbiguousOutcome, match="reconcile"):
        journal.run_once(
            execution_id=RUN, capsule_id=CAPSULE, step_id="send",
            capability_id="message", operation="send", parameters={"synthetic": True},
            guard=FakeGuard(), now=101,
            dispatcher=lambda _: pytest.fail("replayed crashed side effect"))


def test_two_host_connections_cannot_reserve_same_step_twice(tmp_path):
    """Second connection observes STARTED and cannot dispatch concurrently."""
    path = tmp_path / "two-connections.sqlite3"
    first = DurableDispatchJournal(path)
    second = DurableDispatchJournal(path)
    fingerprint = "d" * 64
    assert first._reserve("concurrent-run", "send", fingerprint) is None
    with pytest.raises(AmbiguousOutcome):
        second._reserve("concurrent-run", "send", fingerprint)
    with pytest.raises(JournalConflict):
        second._reserve("concurrent-run", "send", "e" * 64)
    first.close()
    second.close()
