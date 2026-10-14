"""Optional host-side KCC trajectory observation and HMAC provenance demo.

Host MUST control recorder, signing key and Guard/dispatcher. This is neither
an approval provider nor a cryptographic proof of dispatcher coverage.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import inspect
import json
import os
import re
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from kavi_capability_compiler.runtime import AuthorityDenied
from scripts.trajectory_ci import TRACE_VERSION, InvalidArtifact, evaluate, validate_trace

ATTEST_VERSION = "kcc.host-trace-attestation.v0"
HEX64 = re.compile(r"^[a-f0-9]{64}$")
NODE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")
MAX_BUNDLE_BYTES = 1024 * 1024


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def trace_digest(trace: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(trace)).hexdigest()


def _key(key: bytes) -> None:
    if not isinstance(key, bytes) or len(key) < 32:
        raise InvalidArtifact("host attestation key must contain >=32 bytes")


def _identity(value: Any, field: str) -> str:
    if not isinstance(value, str) or not NODE.fullmatch(value):
        raise InvalidArtifact(f"invalid {field}")
    return value


class HostTraceRecorder:
    """Host-controlled sync Guard wrapper; no API for injecting raw model events.

    Events reflect completed dispatcher calls and Guard denials. Unexpected
    dispatcher failure makes a run impossible to finalize. This v0 deliberately
    has no approval emitter: ApprovalRequired is denial, NOT approval.
    """

    def __init__(self, *, execution_id: str, capsule_id: str,
                 emitter_id: str, signing_key: bytes) -> None:
        self.execution_id = _identity(execution_id, "execution_id")
        self.emitter_id = _identity(emitter_id, "emitter_id")
        if not isinstance(capsule_id, str) or not HEX64.fullmatch(capsule_id):
            raise InvalidArtifact("invalid capsule_id")
        self.capsule_id = capsule_id
        _key(signing_key)
        self.__key = signing_key
        self.__events: list[dict[str, str]] = []
        self.__dispatch_count = 0
        self.__faulted = False
        self.__closed = False

    @property
    def faulted(self) -> bool:
        return self.__faulted

    def record_signed_approval(self, *, node_id: str, step_id: str,
                               capability_id: str, operation: str,
                               receipt: dict[str, Any], verifier_key: bytes,
                               actor_id: str, now: int) -> None:
        """Record an approval only after verifying an independent host receipt."""
        if self.__closed or self.__faulted:
            raise InvalidArtifact("trace session closed or failed")
        from scripts.approval_and_journal import verify_receipt
        verify_receipt(receipt, key=verifier_key,
                       execution_id=self.execution_id, capsule_id=self.capsule_id,
                       step_id=step_id, capability_id=capability_id,
                       operation=operation, actor_id=actor_id, now=now)
        self.__events.append({"node_id": _identity(node_id, "node_id"),
                              "kind": "approval", "capability_id": capability_id,
                              "operation": operation, "outcome": "approved"})

    def guarded_call(self, *, node_id: str, guard: Any, capability_id: str,
                     operation: str, parameters: Mapping[str, Any],
                     dispatcher: Callable[[dict[str, Any]], Any],
                     now: int | None = None) -> dict[str, Any]:
        if self.__closed or self.__faulted:
            raise InvalidArtifact("trace session closed or failed")
        node_id = _identity(node_id, "node_id")
        if not isinstance(capability_id, str) or not capability_id or len(capability_id) > 256:
            raise InvalidArtifact("invalid capability_id")
        if not isinstance(operation, str) or not operation or len(operation) > 256:
            raise InvalidArtifact("invalid operation")
        if getattr(guard, "capsule_id", None) != self.capsule_id:
            raise InvalidArtifact("Guard capsule does not match trace run capsule")
        entered = False

        def wrapped(actual_params: dict[str, Any]) -> Any:
            nonlocal entered
            entered = True
            self.__dispatch_count += 1
            try:
                outcome = dispatcher(actual_params)
                if inspect.isawaitable(outcome):
                    if inspect.iscoroutine(outcome):
                        outcome.close()
                    raise TypeError("sync trace wrapper rejects awaitable dispatcher")
            except BaseException:
                self.__faulted = True
                raise
            self.__events.append({"node_id": node_id, "kind": "dispatch",
                                  "capability_id": capability_id,
                                  "operation": operation, "outcome": "executed"})
            return outcome

        try:
            return guard.dispatch_sync(capability_id, wrapped,
                                       operation=operation, parameters=dict(parameters), now=now)
        except AuthorityDenied:
            # A dispatcher may itself raise AuthorityDenied. Never count it
            # as a KCC pre-dispatch denial if dispatcher was entered.
            if entered:
                self.__faulted = True
                raise
            self.__events.append({"node_id": node_id, "kind": "denial",
                                  "capability_id": capability_id,
                                  "operation": operation, "outcome": "denied"})
            raise
        except BaseException:
            self.__faulted = True
            raise

    def finalize(self) -> dict[str, Any]:
        if self.__closed or self.__faulted or not self.__events:
            raise InvalidArtifact("cannot finalize closed, failed or empty run")
        self.__closed = True
        trace = {"version": TRACE_VERSION, "events": list(self.__events)}
        validate_trace(trace)
        attestation: dict[str, Any] = {
            "version": ATTEST_VERSION,
            "execution_id": self.execution_id,
            "capsule_id": self.capsule_id,
            "emitter_id": self.emitter_id,
            "complete": True,
            "event_count": len(self.__events),
            "dispatch_count": self.__dispatch_count,
            "trace_sha256": trace_digest(trace),
        }
        attestation["mac_sha256"] = hmac.new(self.__key, canonical(attestation), hashlib.sha256).hexdigest()
        return {"trace": trace, "attestation": attestation}


def verify_host_bundle(bundle: Any, *, signing_key: bytes,
                       execution_id: str, capsule_id: str,
                       emitter_id: str) -> dict[str, Any]:
    """Verify independent run identity, shape, counts, digest and MAC.

    Key MUST come from verifier environment, never from bundle. MAC does not
    prove completeness of runtime instrumentation or external human approval.
    """
    _key(signing_key)
    if not isinstance(bundle, dict) or set(bundle) != {"trace", "attestation"}:
        raise InvalidArtifact("invalid host bundle fields")
    events = validate_trace(bundle["trace"])
    attestation = bundle["attestation"]
    required = {"version", "execution_id", "capsule_id", "emitter_id", "complete",
                "event_count", "dispatch_count", "trace_sha256", "mac_sha256"}
    if not isinstance(attestation, dict) or set(attestation) != required:
        raise InvalidArtifact("invalid attestation fields")
    if (attestation["version"] != ATTEST_VERSION or attestation["complete"] is not True or
            attestation["execution_id"] != execution_id or
            attestation["capsule_id"] != capsule_id or attestation["emitter_id"] != emitter_id):
        raise InvalidArtifact("host attestation identity/completion mismatch")
    if (not isinstance(attestation["event_count"], int) or
            isinstance(attestation["event_count"], bool) or
            not isinstance(attestation["dispatch_count"], int) or
            isinstance(attestation["dispatch_count"], bool)):
        raise InvalidArtifact("invalid event/dispatch counts")
    if (attestation["event_count"] != len(events) or
            attestation["dispatch_count"] != sum(e["kind"] == "dispatch" for e in events)):
        raise InvalidArtifact("attested event counts mismatch")
    if attestation["trace_sha256"] != trace_digest(bundle["trace"]):
        raise InvalidArtifact("trace digest mismatch")
    if (not isinstance(attestation["mac_sha256"], str) or
            not HEX64.fullmatch(attestation["mac_sha256"])):
        raise InvalidArtifact("invalid attestation mac")
    signed_body = {k: v for k, v in attestation.items() if k != "mac_sha256"}
    mac = hmac.new(signing_key, canonical(signed_body), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, attestation["mac_sha256"]):
        raise InvalidArtifact("host MAC invalid")
    return {"valid": True, "trace_sha256": attestation["trace_sha256"],
            "execution_id": execution_id, "capsule_id": capsule_id, "emitter_id": emitter_id}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify host provenance before DAG trajectory CI")
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--capsule-id", required=True)
    parser.add_argument("--emitter-id", required=True)
    args = parser.parse_args(argv)
    try:
        key_hex = os.environ.get("KCC_TRACE_ATTEST_KEY_HEX", "")
        if not re.fullmatch(r"[0-9a-fA-F]{64,}", key_hex) or len(key_hex) % 2:
            raise InvalidArtifact("KCC_TRACE_ATTEST_KEY_HEX missing or invalid")
        signing_key = bytes.fromhex(key_hex)
        if args.bundle.stat().st_size > MAX_BUNDLE_BYTES:
            raise InvalidArtifact("bundle exceeds 1 MiB")
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
        policy = json.loads(args.policy.read_text(encoding="utf-8"))
        verify_host_bundle(bundle, signing_key=signing_key, execution_id=args.execution_id,
                           capsule_id=args.capsule_id, emitter_id=args.emitter_id)
        report = evaluate(policy, bundle["trace"])
    except (InvalidArtifact, ValueError, OSError, RecursionError, TypeError) as exc:
        print(json.dumps({"pass": False, "findings": [f"invalid host evidence: {exc}"]}))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
