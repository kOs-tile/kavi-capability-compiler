"""Experimental host-owned approval receipt and SQLite idempotent dispatch gate.

A crash after external side effects but before completion is AMBIGUOUS and
must never cause a blind retry. The host owns policy, keys and dispatcher.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Callable, Mapping

from scripts.trusted_trajectory import canonical, InvalidArtifact

RECEIPT_VERSION = "kcc.approval-receipt.v0"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
IDENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


class AmbiguousOutcome(RuntimeError):
    """A side effect may have happened. Reconcile before retrying."""


class JournalConflict(RuntimeError):
    """Step has already been used with incompatible request/state."""


def _ident(value: Any, name: str) -> str:
    if not isinstance(value, str) or not IDENT.fullmatch(value):
        raise InvalidArtifact(f"invalid {name}")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 256 or value != value.strip():
        raise InvalidArtifact(f"invalid {name}")
    return value


def issue_test_receipt(*, key: bytes, execution_id: str, capsule_id: str,
                       step_id: str, capability_id: str, operation: str,
                       actor_id: str, now: int, ttl: int = 60) -> dict[str, Any]:
    """TEST ONLY: a real approved receipt comes from a separate host authority."""
    if not isinstance(key, bytes) or len(key) < 32:
        raise InvalidArtifact("approval signing key too short")
    if type(now) is not int or type(ttl) is not int or not (1 <= ttl <= 300):
        raise InvalidArtifact("invalid receipt lifetime")
    if not isinstance(capsule_id, str) or not HEX64.fullmatch(capsule_id):
        raise InvalidArtifact("invalid capsule_id")
    receipt = {"version": RECEIPT_VERSION,
               "execution_id": _ident(execution_id, "execution_id"),
               "capsule_id": capsule_id, "step_id": _ident(step_id, "step_id"),
               "capability_id": _text(capability_id, "capability_id"),
               "operation": _text(operation, "operation"),
               "actor_id": _ident(actor_id, "actor_id"), "decision": "approved",
               "issued_at": now, "expires_at": now + ttl}
    receipt["mac_sha256"] = hmac.new(key, canonical(receipt), hashlib.sha256).hexdigest()
    return receipt


def verify_receipt(receipt: Any, *, key: bytes, execution_id: str,
                   capsule_id: str, step_id: str, capability_id: str,
                   operation: str, actor_id: str, now: int) -> None:
    if not isinstance(key, bytes) or len(key) < 32:
        raise InvalidArtifact("approval verifier key too short")
    required = {"version", "execution_id", "capsule_id", "step_id", "capability_id",
                "operation", "actor_id", "decision", "issued_at", "expires_at", "mac_sha256"}
    if not isinstance(receipt, dict) or set(receipt) != required:
        raise InvalidArtifact("approval receipt invalid fields")
    expected = {"version": RECEIPT_VERSION,
                "execution_id": _ident(execution_id, "execution_id"),
                "capsule_id": capsule_id, "step_id": _ident(step_id, "step_id"),
                "capability_id": _text(capability_id, "capability_id"),
                "operation": _text(operation, "operation"),
                "actor_id": _ident(actor_id, "actor_id"), "decision": "approved"}
    if any(receipt[k] != v for k, v in expected.items()):
        raise InvalidArtifact("approval identity or decision mismatch")
    issued, expires = receipt["issued_at"], receipt["expires_at"]
    if (type(now) is not int or type(issued) is not int or type(expires) is not int
            or not issued <= now < expires or not 1 <= expires - issued <= 300):
        raise InvalidArtifact("approval receipt expired, future or invalid lifetime")
    signed = {k: v for k, v in receipt.items() if k != "mac_sha256"}
    mac = hmac.new(key, canonical(signed), hashlib.sha256).hexdigest()
    signature = receipt["mac_sha256"]
    if not isinstance(signature, str) or not HEX64.fullmatch(signature):
        raise InvalidArtifact("approval signature malformed")
    if not hmac.compare_digest(mac, signature):
        raise InvalidArtifact("approval signature mismatch")


class DurableDispatchJournal:
    """Disk-backed step barrier; no automatic retry for in-flight effects.

    A STARTED row is committed *before* invoking Guard and the dispatcher.
    A restarted process returns persisted results of completed calls, but any
    STARTED row is ambiguous until independently reconciled by the operator.
    """

    def __init__(self, path: str | Path, *,
                 approval_required: frozenset[tuple[str, str]] = frozenset()):
        self._approval_required = frozenset(approval_required)
        path = Path(path)
        if str(path) == ":memory:":
            raise InvalidArtifact("journal must be durable on disk")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), isolation_level=None, timeout=5)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS steps (
            execution_id TEXT NOT NULL, step_id TEXT NOT NULL,
            request_sha256 TEXT NOT NULL, state TEXT NOT NULL,
            result_json TEXT, PRIMARY KEY (execution_id, step_id)
        )""")

    def close(self) -> None:
        self.db.close()

    def _reserve(self, execution_id: str, step_id: str, fingerprint: str) -> Any:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute(
                "SELECT request_sha256,state,result_json FROM steps WHERE execution_id=? AND step_id=?",
                (execution_id, step_id)).fetchone()
            if row is None:
                self.db.execute(
                    "INSERT INTO steps(execution_id,step_id,request_sha256,state) VALUES (?,?,?,'started')",
                    (execution_id, step_id, fingerprint))
                self.db.execute("COMMIT")
                return None
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        if row[0] != fingerprint:
            raise JournalConflict("step reused with different operation, arguments or approval")
        if row[1] == "completed":
            return {"state": "already_completed", "result": json.loads(row[2])}
        if row[1] == "denied":
            raise JournalConflict("step previously denied; new approval requires a new step")
        raise AmbiguousOutcome("step started previously; execution outcome unknown, reconcile before retry")

    def _finish(self, execution_id: str, step_id: str, state: str, result: Any = None) -> None:
        row = self.db.execute(
            "UPDATE steps SET state=?, result_json=? WHERE execution_id=? AND step_id=? AND state='started'",
            (state, json.dumps(result, sort_keys=True, allow_nan=False) if state == "completed" else None,
             execution_id, step_id))
        if row.rowcount != 1:
            raise JournalConflict("missing pending step")

    def run_once(self, *, execution_id: str, capsule_id: str, step_id: str,
                 capability_id: str, operation: str, parameters: Mapping[str, Any],
                 guard: Any, dispatcher: Callable[[dict[str, Any]], Any], now: int,
                 approval_receipt: dict[str, Any] | None = None,
                 approval_key: bytes | None = None, expected_approver: str | None = None,
                 recorder: Any | None = None,
                 approval_node_id: str | None = None) -> dict[str, Any]:
        _ident(execution_id, "execution_id")
        _ident(step_id, "step_id")
        _text(capability_id, "capability_id")
        _text(operation, "operation")
        if not isinstance(capsule_id, str) or not HEX64.fullmatch(capsule_id):
            raise InvalidArtifact("invalid capsule_id")
        if getattr(guard, "capsule_id", None) != capsule_id:
            raise InvalidArtifact("Guard/capsule mismatch")
        if (capability_id, operation) in self._approval_required and approval_receipt is None:
            raise InvalidArtifact("host policy requires signed approval receipt")
        if (approval_receipt is None) != (approval_key is None):
            raise InvalidArtifact("approval receipt and key must both be present")
        if approval_receipt is not None:
            if not isinstance(expected_approver, str) or not approval_node_id:
                raise InvalidArtifact("trusted approval actor and node required")
            _ident(approval_node_id, "approval_node_id")
            verify_receipt(approval_receipt, key=approval_key, execution_id=execution_id,
                           capsule_id=capsule_id, step_id=step_id,
                           capability_id=capability_id, operation=operation,
                           actor_id=expected_approver, now=now)
            if recorder is None:
                raise InvalidArtifact("approval requires host trace recorder")
        request = {"execution_id": execution_id, "capsule_id": capsule_id,
                   "step_id": step_id, "capability_id": capability_id,
                   "operation": operation, "parameters": dict(parameters),
                   "approval_mac": approval_receipt["mac_sha256"] if approval_receipt else None}
        fingerprint = hashlib.sha256(canonical(request)).hexdigest()
        existing = self._reserve(execution_id, step_id, fingerprint)
        if existing is not None:
            return existing
        try:
            if approval_receipt is not None:
                recorder.record_signed_approval(
                    node_id=approval_node_id, step_id=step_id,
                    capability_id=capability_id, operation=operation,
                    receipt=approval_receipt, verifier_key=approval_key,
                    actor_id=expected_approver, now=now)
            if recorder is not None:
                result = recorder.guarded_call(
                    node_id=step_id, guard=guard, capability_id=capability_id,
                    operation=operation, parameters=parameters,
                    dispatcher=dispatcher, now=now)
            else:
                result = guard.dispatch_sync(
                    capability_id, dispatcher, operation=operation,
                    parameters=parameters, now=now)
        except Exception as exc:
            from kavi_capability_compiler.runtime import AuthorityDenied
            # Only the host recorder can distinguish a true pre-dispatch Guard
            # denial from an exception thrown *inside* the dispatcher.
            if isinstance(exc, AuthorityDenied) and recorder is not None:
                if not getattr(recorder, "faulted", True):
                    self._finish(execution_id, step_id, "denied")
            raise
        try:
            self._finish(execution_id, step_id, "completed", result)
        except Exception as exc:
            raise AmbiguousOutcome("dispatcher finished but durable completion failed") from exc
        return {"state": "completed", "result": result}
