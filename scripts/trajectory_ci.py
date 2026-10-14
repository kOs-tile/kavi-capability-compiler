"""Offline, deterministic observation-only trajectory gate for agent tool traces.

This checker does NOT grant/revoke runtime authority. It compares a trusted
host-emitted trace against an explicit expected partial-order DAG in CI.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

POLICY_VERSION = "kcc.trajectory-policy.v0"
TRACE_VERSION = "kcc.trajectory-trace.v0"
KINDS = {"dispatch": "executed", "approval": "approved", "denial": "denied"}
ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")
MAX_FILE = 1024 * 1024
MAX_NODES = 256
MAX_EVENTS = 1024


class InvalidArtifact(ValueError):
    """Invalid policy or trace: reject rather than attempting to guess intent."""


def _required_object(value: Any, where: str, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise InvalidArtifact(f"{where}: expected keys {sorted(keys)}")
    return value


def _field(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 256 or value.strip() != value:
        raise InvalidArtifact(f"{where}: expected nonempty trimmed string <=256 chars")
    return value


def _node_id(value: Any, where: str) -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise InvalidArtifact(f"{where}: invalid node id")
    return value


def validate_policy(policy: Any) -> dict[str, dict[str, Any]]:
    root = _required_object(policy, "policy", {"version", "nodes"})
    if root["version"] != POLICY_VERSION:
        raise InvalidArtifact("policy: unsupported version")
    raw = root["nodes"]
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_NODES:
        raise InvalidArtifact("policy.nodes: expected 1..256 nodes")
    nodes: dict[str, dict[str, Any]] = {}
    for i, item in enumerate(raw):
        obj = _required_object(item, f"policy.nodes[{i}]", {
            "id", "kind", "capability_id", "operation", "after"
        })
        node = _node_id(obj["id"], f"policy.nodes[{i}].id")
        if node in nodes:
            raise InvalidArtifact(f"duplicate policy node: {node}")
        if obj["kind"] not in KINDS:
            raise InvalidArtifact(f"{node}: unsupported event kind")
        _field(obj["capability_id"], f"{node}.capability_id")
        _field(obj["operation"], f"{node}.operation")
        deps = obj["after"]
        if (not isinstance(deps, list) or len(deps) > MAX_NODES
                or any(not isinstance(dep, str) for dep in deps)
                or len(deps) != len(set(deps))):
            raise InvalidArtifact(f"{node}: invalid after dependencies")
        nodes[node] = obj
    for node, obj in nodes.items():
        if any(dep not in nodes or dep == node for dep in obj["after"]):
            raise InvalidArtifact(f"{node}: unknown or self dependency")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise InvalidArtifact("policy: dependency cycle")
        if node in visited:
            return
        visiting.add(node)
        for dep in nodes[node]["after"]:
            visit(dep)
        visiting.remove(node)
        visited.add(node)

    for node in nodes:
        visit(node)
    return nodes


def validate_trace(trace: Any) -> list[dict[str, Any]]:
    root = _required_object(trace, "trace", {"version", "events"})
    if root["version"] != TRACE_VERSION:
        raise InvalidArtifact("trace: unsupported version")
    events = root["events"]
    if not isinstance(events, list) or len(events) > MAX_EVENTS:
        raise InvalidArtifact("trace.events: expected at most 1024 events")
    for i, raw in enumerate(events):
        obj = _required_object(raw, f"trace.events[{i}]", {
            "node_id", "kind", "capability_id", "operation", "outcome"
        })
        _node_id(obj["node_id"], f"trace.events[{i}].node_id")
        for key in ("capability_id", "operation"):
            _field(obj[key], f"trace.events[{i}].{key}")
        if obj["kind"] not in KINDS or obj["outcome"] not in KINDS.values():
            raise InvalidArtifact(f"trace.events[{i}]: invalid kind/outcome")
    return events


def evaluate(policy: Any, trace: Any) -> dict[str, Any]:
    """Evaluate the exact observed tool/approval/denial steps vs a golden DAG.

    Every golden node is required exactly once. Independent nodes may commute.
    Unknown, duplicate, mismatched or out-of-order events fail closed.
    """
    nodes = validate_policy(policy)
    events = validate_trace(trace)
    completed: set[str] = set()
    findings: list[str] = []
    for index, event in enumerate(events):
        node_id = event["node_id"]
        expected = nodes.get(node_id)
        if expected is None:
            findings.append(f"event[{index}]: unknown node {node_id}")
            continue
        if node_id in completed:
            findings.append(f"event[{index}]: duplicate node {node_id}")
            continue
        expected_fields = {"kind": expected["kind"],
                           "capability_id": expected["capability_id"],
                           "operation": expected["operation"],
                           "outcome": KINDS[expected["kind"]]}
        if any(event[field] != value for field, value in expected_fields.items()):
            findings.append(f"event[{index}]: mismatch for node {node_id}")
            continue
        missing_deps = sorted(set(expected["after"]) - completed)
        if missing_deps:
            findings.append(f"event[{index}]: {node_id} before {','.join(missing_deps)}")
            continue
        completed.add(node_id)
    missing = sorted(set(nodes) - completed)
    if missing:
        findings.append(f"missing required nodes: {','.join(missing)}")
    return {"version": "kcc.trajectory-result.v0", "pass": not findings,
            "node_count": len(nodes), "event_count": len(events), "findings": findings}


def _load(path: Path) -> Any:
    if path.stat().st_size > MAX_FILE:
        raise InvalidArtifact(f"{path}: file exceeds 1 MiB")
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail-closed, read-only agent trajectory CI evaluator")
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = evaluate(_load(args.policy), _load(args.trace))
    except (InvalidArtifact, ValueError, OSError, RecursionError) as exc:
        report = {"version": "kcc.trajectory-result.v0", "pass": False,
                  "findings": [f"invalid input: {exc}"]}
        print(json.dumps(report, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
