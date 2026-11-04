"""Synthetic Groq capture reconciliation. Never contacts network."""
from __future__ import annotations
import copy
import json
from pathlib import Path

import pytest

from evals import groq_chat_probe as g
from evals.summarize_groq_run import audit
from evals.openai_responses_probe import EvidenceError

DATA = Path(__file__).resolve().parents[1] / "evals" / "agent_tool_benchmark_public_dev_40.json"


def dataset():
    return g.parse_dataset(json.loads(DATA.read_text(encoding="utf-8")))


def row(case, *, rep=0, model="openai/gpt-oss-20b", response_id=None,
        valid=True):
    cap = 384
    proposals = ([{"tool": "read_record", "parameters": {"customer_id": "tenant-a-001"}}]
                 if valid else [{"tool": "delete_record", "parameters":
                                  {"customer_id": "tenant-a-001"}}])
    return {
        "schema_version": g.OUTPUT_VERSION,
        "source_type": g.SOURCE,
        "case_id": case["id"], "kind": case["kind"],
        "repetition": rep, "model": model, "ingress_mode": "tool_result",
        "provider_model_reported": model,
        "dataset_sha256": g.sha256(dataset()),
        "request_sha256": g.sha256(g.make_chat_request(
            case, model=model, max_completion_tokens=cap)),
        "max_completion_tokens": cap,
        "provider_response_id": response_id or f"MOCK-{model}-{case['id']}-{rep}",
        "finish_reason": "tool_calls", "conclusive": True,
        "proposals": proposals, "guard": g.judge_proposals(proposals),
        "usage": {"input_tokens": 150, "output_tokens": 40},
        "external_tool_dispatches": 0,
        "provider_authentication": "CLIENT_OBSERVED_ONLY",
        "free_plan_status": "USER_ATTESTED_NOT_PROVIDER_VERIFIED",
    }


def records(tmp_path, entries):
    path = tmp_path / "fake-client-capture.jsonl"
    path.write_text("".join(json.dumps(entry) + "\n" for entry in entries))
    return path


def test_complete_synthetic_40_case_audit(tmp_path):
    data = dataset()
    rows = [row(c) for c in data["cases"]]
    report = audit(data, [records(tmp_path, rows)], expected_repetitions=1)
    summary = report["models"][0]
    assert summary["planned_trials"] == 40
    assert summary["recorded_trials"] == 40
    assert summary["complete_trial_capture"]
    assert summary["guard_allowed_proposals"] == 40
    assert summary["actual_tool_dispatches"] == 0
    assert not report["provider_signature_independently_verified"]
    assert not report["free_org_tier_independently_verified"]


def test_missing_repetitions_are_not_assumed_safe(tmp_path):
    data = dataset()
    report = audit(data, [records(tmp_path, [row(data["cases"][0])])],
                   expected_repetitions=3)
    summary = report["models"][0]
    assert summary["planned_trials"] == 120
    assert summary["recorded_trials"] == 1
    assert len(summary["missing_trials"]) == 119
    assert not summary["complete_trial_capture"]


def test_attack_proposal_risk_separated_from_guard_denial(tmp_path):
    data = dataset()
    report = audit(data, [records(tmp_path, [row(data["cases"][0], valid=False)])],
                   expected_repetitions=1)
    summary = report["models"][0]
    assert summary["attack_with_unsafe_proposal"] == 1
    assert summary["guard_denied_proposals"] == 1
    assert summary["actual_tool_dispatches"] == 0


def test_cannot_replay_falsely_safe_guard_decision(tmp_path):
    data = dataset()
    fake = row(data["cases"][0], valid=False)
    fake["guard"]["guard_blocked_proposals"] = 0
    with pytest.raises(EvidenceError, match="Guard decision"):
        audit(data, [records(tmp_path, [fake])], expected_repetitions=1)


def test_dataset_hash_drift_fails(tmp_path):
    data = dataset()
    fake = row(data["cases"][0])
    fake["dataset_sha256"] = "0" * 64
    with pytest.raises(EvidenceError, match="dataset SHA"):
        audit(data, [records(tmp_path, [fake])], expected_repetitions=1)


def test_request_hash_must_match_frozen_test_case(tmp_path):
    data = dataset()
    fake = row(data["cases"][0])
    fake["request_sha256"] = "0" * 64
    with pytest.raises(EvidenceError, match="request digest"):
        audit(data, [records(tmp_path, [fake])], expected_repetitions=1)


def test_duplicate_response_id_rejected(tmp_path):
    data = dataset()
    a, b = row(data["cases"][0]), row(data["cases"][1])
    b["provider_response_id"] = a["provider_response_id"]
    with pytest.raises(EvidenceError, match="duplicate provider response"):
        audit(data, [records(tmp_path, [a, b])], expected_repetitions=1)


def test_duplicate_case_repetition_rejected(tmp_path):
    data = dataset()
    a = row(data["cases"][0])
    b = copy.deepcopy(a)
    b["provider_response_id"] = "MOCK-OTHER-RESPONSE-ID"
    with pytest.raises(EvidenceError, match="duplicate model case"):
        audit(data, [records(tmp_path, [a, b])], expected_repetitions=1)


def test_incomplete_response_is_not_model_safety_pass(tmp_path):
    data = dataset()
    a = row(data["cases"][0])
    a["finish_reason"] = "length"
    a["conclusive"] = False
    a["guard"] = None
    result = audit(data, [records(tmp_path, [a])], expected_repetitions=1)
    assert result["models"][0]["incomplete_trials"] == 1
    assert result["models"][0]["attack_completed"] == 0
    assert result["models"][0]["conditional_unsafe_proposal_rate_on_completed_attack_cases"] is None


def test_wrong_ingress_tag_fails(tmp_path):
    data = dataset()
    a = row(data["cases"][0])
    a["ingress_mode"] = "unknown_ingress"
    with pytest.raises(EvidenceError, match="ingress mode"):
        audit(data, [records(tmp_path, [a])], expected_repetitions=1)


def test_wrong_source_tag_fails(tmp_path):
    data = dataset()
    a = row(data["cases"][0])
    a["source_type"] = "TEST_FIXTURE_NOT_REAL"
    with pytest.raises(EvidenceError, match="unrecognized Groq"):
        audit(data, [records(tmp_path, [a])], expected_repetitions=1)
