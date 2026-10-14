"""Deterministic trajectory gate tests; synthetic fixtures have no authority."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.trajectory_ci import InvalidArtifact, evaluate

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples" / "trajectory"
POLICY = json.loads((FIXTURES / "policy.json").read_text())
PASS = json.loads((FIXTURES / "pass.json").read_text())


def test_good_trace_passes():
    result = evaluate(POLICY, PASS)
    assert result["pass"] is True
    assert result["findings"] == []
    assert result["node_count"] == 3


def test_unordered_independent_nodes_allowed():
    policy = copy.deepcopy(POLICY)
    policy["nodes"][1]["after"] = []
    trace = copy.deepcopy(PASS)
    trace["events"][0], trace["events"][1] = trace["events"][1], trace["events"][0]
    assert evaluate(policy, trace)["pass"] is True


def test_approval_bypass_rejected():
    trace = copy.deepcopy(PASS)
    trace["events"].pop(1)
    result = evaluate(POLICY, trace)
    assert result["pass"] is False
    assert any("before approve" in line for line in result["findings"])


def test_approval_requested_is_not_approval_granted():
    trace = copy.deepcopy(PASS)
    trace["events"][1]["outcome"] = "denied"
    assert evaluate(POLICY, trace)["pass"] is False


def test_unexpected_delete_rejected():
    trace = copy.deepcopy(PASS)
    trace["events"].append({"node_id": "delete", "kind": "dispatch",
                            "capability_id": "mcp:crm:delete", "operation": "delete",
                            "outcome": "executed"})
    assert any("unknown node delete" in line for line in evaluate(POLICY, trace)["findings"])


def test_wrong_tool_or_operation_rejected():
    for field, value in (("capability_id", "mcp:crm:delete"), ("operation", "delete"),
                         ("kind", "denial")):
        trace = copy.deepcopy(PASS)
        trace["events"][0][field] = value
        assert evaluate(POLICY, trace)["pass"] is False


def test_duplicate_dispatch_rejected():
    trace = copy.deepcopy(PASS)
    trace["events"].append(dict(trace["events"][0]))
    assert any("duplicate node" in line for line in evaluate(POLICY, trace)["findings"])


def test_missing_node_rejected():
    trace = copy.deepcopy(PASS)
    trace["events"].pop()
    assert any("missing required nodes" in line for line in evaluate(POLICY, trace)["findings"])


def test_unknown_node_and_bad_shape_rejected():
    trace = copy.deepcopy(PASS)
    trace["events"][0]["node_id"] = "unknown"
    assert evaluate(POLICY, trace)["pass"] is False
    trace["events"][0]["parameters"] = {"secret": "not permitted"}
    with pytest.raises(InvalidArtifact):
        evaluate(POLICY, trace)


def test_invalid_dag_rejected():
    policy = copy.deepcopy(POLICY)
    policy["nodes"][0]["after"] = ["send"]
    with pytest.raises(InvalidArtifact, match="cycle"):
        evaluate(policy, PASS)


def test_missing_dependency_rejected():
    policy = copy.deepcopy(POLICY)
    policy["nodes"][0]["after"] = ["unknown"]
    with pytest.raises(InvalidArtifact):
        evaluate(policy, PASS)


def test_cli_exit_codes():
    command = [sys.executable, str(ROOT / "scripts" / "trajectory_ci.py"),
               "--policy", str(FIXTURES / "policy.json"), "--trace"]
    ok = subprocess.run(command + [str(FIXTURES / "pass.json")], capture_output=True, text=True)
    bad = subprocess.run(command + [str(FIXTURES / "fail.json")], capture_output=True, text=True)
    assert ok.returncode == 0 and json.loads(ok.stdout)["pass"] is True
    assert bad.returncode == 1 and json.loads(bad.stdout)["pass"] is False
