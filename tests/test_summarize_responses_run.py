"""Evidence aggregator tests use synthetic records, never API network or models."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import pytest
from evals.openai_responses_probe import make_request, parse_dataset, sha256
from evals.summarize_responses_run import EvidenceError, summarize

DATASET = Path(__file__).resolve().parents[1] / "evals" / "agent_tool_benchmark_public_dev_40.json"


def data():
    return parse_dataset(json.loads(DATASET.read_text(encoding="utf-8")))


def one_record(case, *, model="fake-simulated-model", repeat=0, position=0):
    token_cap = 384
    payload = make_request(case, model=model, max_output_tokens=token_cap)
    return {
        "case_id": case["id"], "kind": case["kind"], "repetition": repeat,
        "model": model,
        "provider_response_id": f"NOT-REAL-{model}-{repeat}-{position}",
        "provider_status": "completed",
        "dataset_sha256": sha256(data()),
        "request_sha256": sha256(payload),
        "max_output_tokens": token_cap,
        "usage": {"input_tokens": 150, "output_tokens": 20},
        "estimated_cost_usd": "0.00025",
        "judge": {
            "proposed_calls": 1,
            "guard_allowed_proposals": 1,
            "guard_blocked_proposals": 0,
            "suggested_unauthorized_calls": 0,
            "actual_dispatches": 0,
        },
        "source_type": "DIRECT_RESPONSES_API_FUNCTION_CALL_PROPOSALS",
        "no_external_dispatch": True,
    }


def write_records(tmp_path, records, name="synthetic.jsonl"):
    p = tmp_path / name
    p.write_text("".join(json.dumps(x) + "\n" for x in records), encoding="utf-8")
    return p


def test_full_40_replay_aggregates_but_never_authenticates_model_origin(tmp_path):
    d = data()
    rows = [one_record(c, position=i) for i, c in enumerate(d["cases"])]
    result = summarize(d, [write_records(tmp_path, rows)], expected_repetitions=1)
    r = result["models"][0]
    assert r["captured_responses"] == 40
    assert r["expected_trials"] == 40
    assert r["completed_attack_trials"] == 30
    assert r["completed_benign_trials"] == 10
    assert r["is_complete_in_observed_repetition_span"] is True
    assert result["independent_provider_provenance_verified"] is False
    assert result["external_dispatched_tool_calls"] == 0


def test_missing_future_repetitions_cannot_pass(tmp_path):
    d = data()
    rows = [one_record(c, position=i) for i, c in enumerate(d["cases"])]
    result = summarize(d, [write_records(tmp_path, rows)], expected_repetitions=3)
    r = result["models"][0]
    assert r["expected_trials"] == 120
    assert r["captured_responses"] == 40
    assert len(r["missing_case_repetition_pairs"]) == 80
    assert not r["is_complete_in_observed_repetition_span"]


def test_replay_duplicate_trial_rejected(tmp_path):
    d = data()
    row = one_record(d["cases"][0])
    duplicate = copy.deepcopy(row)
    duplicate["provider_response_id"] = "NOT-REAL-OTHER-ID"
    with pytest.raises(EvidenceError, match="duplicate trial"):
        summarize(d, [write_records(tmp_path, [row, duplicate])], expected_repetitions=1)


def test_replay_duplicate_response_id_rejected(tmp_path):
    d = data()
    rows = [one_record(d["cases"][i], position=0) for i in (0, 1)]
    with pytest.raises(EvidenceError, match="duplicate response id"):
        summarize(d, [write_records(tmp_path, rows)], expected_repetitions=1)


def test_request_digest_tamper_rejected(tmp_path):
    d = data()
    row = one_record(d["cases"][0])
    row["request_sha256"] = "0" * 64
    with pytest.raises(EvidenceError, match="request digest"):
        summarize(d, [write_records(tmp_path, [row])], expected_repetitions=1)


def test_source_type_tamper_rejected(tmp_path):
    d = data()
    row = one_record(d["cases"][0])
    row["source_type"] = "scripted_fixture"
    with pytest.raises(EvidenceError, match="direct API"):
        summarize(d, [write_records(tmp_path, [row])], expected_repetitions=1)


def test_incomplete_does_not_count_as_safe_task(tmp_path):
    d = data()
    row = one_record(d["cases"][0])
    row["provider_status"] = "incomplete"
    row["judge"] = None
    result = summarize(d, [write_records(tmp_path, [row])], expected_repetitions=1)
    assert result["models"][0]["inconclusive_responses"] == 1
    assert result["models"][0]["completed_attack_trials"] == 0
    assert result["models"][0]["unsafe_proposal_rate_completed_attack_trials"] is None


def test_invalid_judge_denominator_rejected(tmp_path):
    d = data()
    row = one_record(d["cases"][0])
    row["judge"]["proposed_calls"] = 2
    with pytest.raises(EvidenceError, match="judge counts"):
        summarize(d, [write_records(tmp_path, [row])], expected_repetitions=1)


def test_different_model_ids_remain_separate(tmp_path):
    d = data()
    rows = [one_record(d["cases"][0], model="fake-A"),
            one_record(d["cases"][0], model="fake-B")]
    result = summarize(d, [write_records(tmp_path, rows)], expected_repetitions=1)
    assert {r["model"] for r in result["models"]} == {"fake-A", "fake-B"}
    assert all(len(r["missing_case_repetition_pairs"]) == 39 for r in result["models"])
