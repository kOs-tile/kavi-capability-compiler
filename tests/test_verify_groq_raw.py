"""Offline raw-response replay tests. No real Groq calls or customer tools."""
from __future__ import annotations
import json
import pytest
from pathlib import Path

from evals import groq_chat_probe as groq
from evals.verify_groq_raw import reconcile
from evals.openai_responses_probe import EvidenceError

ROOT = Path(__file__).resolve().parents[1] / "evals"


def dataset():
    return groq.parse_dataset(
        json.loads((ROOT / "agent_tool_benchmark_public_dev_40.json").read_text()))


def fake_response(*, rid: str, name: str = "read_record",
                  args: str = '{"customer_id":"tenant-a-001"}'):
    return {
        "object": "chat.completion",
        "model": "openai/gpt-oss-20b",
        "id": rid,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant",
                        "tool_calls": [{
                            "type": "function",
                            "id": "call_1",
                            "function": {"name": name, "arguments": args},
                        }]},
            "finish_reason": "tool_calls",
        }],
        "usage": {"prompt_tokens": 120, "completion_tokens": 12},
    }


def run_fake(tmp_path, monkeypatch, *, invalid=False, count=2):
    data = dataset()
    plan = groq.build_plan(
        data, model="openai/gpt-oss-20b", case_limit=count, repeat=1,
        max_requests=count, max_completion_tokens=384,
        min_interval_seconds=5)
    sent = []
    def fake_chat(request, key, timeout):
        assert key == "FAKE_LOCAL_KEY"
        sent.append(request)
        return fake_response(
            rid=f"FAKE-GROQ-ID-{len(sent)}",
            args="{not json" if invalid else '{"customer_id":"tenant-a-001"}',
        )
    monkeypatch.setattr(groq, "post_chat", fake_chat)
    clock = iter(range(100, 500, 10))
    output = tmp_path / "capture.jsonl"
    run = lambda: groq.run_free(
        data, plan, api_key="FAKE_LOCAL_KEY", target=output,
        execute_free=True, confirm_org_free_tier=True,
        timeout_seconds=2, sleep_fn=lambda _: None,
        clock_fn=lambda: next(clock))
    if invalid:
        with pytest.raises(EvidenceError, match="not JSON"):
            run()
    else:
        run()
    return data, output, Path(str(output) + ".raw-responses.jsonl"), sent


def rewrite(path, rows):
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def load(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_recompute_scored_guards_from_raw_client_logs(tmp_path, monkeypatch):
    data, score, raw, sent = run_fake(tmp_path, monkeypatch, count=2)
    result = reconcile(data, raw, score)
    assert len(sent) == 2
    assert result["raw_records"] == result["scored_records"] == 2
    assert result["reconstructed_scored_records"] == 2
    assert result["unscorable_raw_records"] == 0
    assert result["provider_attestation_verified"] is False


def test_tampered_guard_is_rejected(tmp_path, monkeypatch):
    data, score, raw, _ = run_fake(tmp_path, monkeypatch)
    records = load(score)
    records[0]["guard"]["guard_blocked_proposals"] = 100
    rewrite(score, records)
    with pytest.raises(EvidenceError, match="raw/scored mismatch.*guard"):
        reconcile(data, raw, score)


def test_raw_response_sha_mutation_rejected(tmp_path, monkeypatch):
    data, score, raw, _ = run_fake(tmp_path, monkeypatch)
    records = load(raw)
    records[0]["response_sha256"] = "0" * 64
    rewrite(raw, records)
    with pytest.raises(EvidenceError, match="raw response digest mismatch"):
        reconcile(data, raw, score)


def test_rehashed_raw_mutation_disagrees_with_scored_record(tmp_path, monkeypatch):
    data, score, raw, _ = run_fake(tmp_path, monkeypatch)
    records = load(raw)
    records[0]["response"]["choices"][0]["message"]["tool_calls"][0][
        "function"]["name"] = "delete_record"
    records[0]["response_sha256"] = groq.sha256(records[0]["response"])
    rewrite(raw, records)
    with pytest.raises(EvidenceError, match="raw/scored mismatch"):
        reconcile(data, raw, score)


def test_scored_orphan_without_raw_rejected(tmp_path, monkeypatch):
    data, score, raw, _ = run_fake(tmp_path, monkeypatch)
    rewrite(raw, load(raw)[:1])
    with pytest.raises(EvidenceError, match="without raw source"):
        reconcile(data, raw, score)


def test_unscorable_raw_record_is_reported_not_marked_safe(tmp_path, monkeypatch):
    data, score, raw, _ = run_fake(tmp_path, monkeypatch, invalid=True, count=1)
    result = reconcile(data, raw, score)
    assert result["raw_records"] == 1
    assert result["scored_records"] == 0
    assert result["unscorable_raw_records"] == 1
    assert result["unscorable"][0]["category"] == "unscorable_provider_output"


def test_duplicate_raw_trial_rejected(tmp_path, monkeypatch):
    data, score, raw, _ = run_fake(tmp_path, monkeypatch)
    records = load(raw)
    rewrite(raw, records + [records[0]])
    with pytest.raises(EvidenceError, match="duplicate raw trial"):
        reconcile(data, raw, score)


def test_invalid_dataset_digest_rejected(tmp_path, monkeypatch):
    data, score, raw, _ = run_fake(tmp_path, monkeypatch)
    records = load(raw)
    records[0]["dataset_sha256"] = "0" * 64
    rewrite(raw, records)
    with pytest.raises(EvidenceError, match="raw dataset digest mismatch"):
        reconcile(data, raw, score)


def test_edited_requested_tool_schema_makes_old_digest_fail(tmp_path, monkeypatch):
    data, score, raw, _ = run_fake(tmp_path, monkeypatch)
    records = load(raw)
    records[0]["max_completion_tokens"] = 500
    rewrite(raw, records)
    with pytest.raises(EvidenceError, match="raw request digest"):
        reconcile(data, raw, score)
