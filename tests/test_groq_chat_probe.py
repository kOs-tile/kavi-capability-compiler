"""Groq free-plan preflight, no-network parser and mocked transport tests."""
from __future__ import annotations

import copy
import io
import json
import os
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

from evals import groq_chat_probe as g

ROOT = Path(__file__).resolve().parents[1] / "evals"
DATA = ROOT / "agent_tool_benchmark_public_dev_40.json"


def dataset():
    return g.parse_dataset(json.loads(DATA.read_text(encoding="utf-8")))


def plan(*, model="openai/gpt-oss-20b", case_limit=4):
    return g.build_plan(
        dataset(), model=model, case_limit=case_limit, repeat=1,
        max_requests=case_limit, max_completion_tokens=384,
        min_interval_seconds=5.0,
    )


def completion(*, tool="read_record", args='{"customer_id":"tenant-a-001"}',
               finish="tool_calls", rid="fake-groq-response"):
    return {
        "id": rid, "object": "chat.completion",
        "model": "openai/gpt-oss-20b",
        "choices": [{
            "index": 0, "finish_reason": finish,
            "message": {"role": "assistant",
                        "tool_calls": [{
                            "id": "call-fake-1", "type": "function",
                            "function": {"name": tool, "arguments": args},
                        }] if tool else []},
        }],
        "usage": {"prompt_tokens": 150, "completion_tokens": 34, "total_tokens": 184},
    }


def test_plan_offline_only_and_interleaves_attack_benign():
    p = plan()
    assert p["network_called"] is False
    assert p["api_spend_initiated"] is False
    assert p["free_tier_required"] is True
    assert p["case_ids"] == ["ATK01", "BEN01", "ATK02", "BEN02"]
    assert p["endpoint"] == "https://api.groq.com/openai/v1/chat/completions"
    assert p["dataset_sha256"] == "bf2897b9f34ad3c885ee75453a0839ca4e5c7cedeb72a2d4be81a16e1ae11497"


def test_all_40_cases_and_three_repetitions():
    p = g.build_plan(dataset(), model="qwen/qwen3.8-27b", case_limit=40,
                     repeat=3, max_requests=120, max_completion_tokens=384,
                     min_interval_seconds=5)
    assert p["request_count"] == 120
    assert len(set(p["case_ids"])) == 40


def test_reject_unrecognized_model():
    with pytest.raises(g.EvidenceError, match="allowlist"):
        g.build_plan(dataset(), model="unverified/bogus", case_limit=8,
                     repeat=1, max_requests=8, max_completion_tokens=384,
                     min_interval_seconds=5)


def test_reject_imprudent_request_rate():
    with pytest.raises(g.EvidenceError, match="pacing"):
        g.build_plan(dataset(), model="openai/gpt-oss-20b",
                     case_limit=8, repeat=1, max_requests=8,
                     max_completion_tokens=384, min_interval_seconds=0.1)


def test_groq_request_is_synthetic_and_no_built_in_tools():
    req = g.make_chat_request(dataset()["cases"][0],
                              model="openai/gpt-oss-20b",
                              max_completion_tokens=384)
    assert req["parallel_tool_calls"] is False
    assert req["tool_choice"] == "auto"
    assert req["stream"] is False
    assert req["messages"][0]["role"] == "system"
    assert req["messages"][1]["role"] == "user"
    assert {x["function"]["name"] for x in req["tools"]} == {
        "read_record", "delete_record", "send_message"}
    assert all(x["type"] == "function" for x in req["tools"])
    assert "browser_search" not in json.dumps(req)
    assert "code_interpreter" not in json.dumps(req)


def test_function_proposals_preserved_for_guard():
    value = g.parse_chat_completion(completion(
        tool="read_record",
        args='{"customer_id":"tenant-a-001","all_tenants":true}'))
    assert value["conclusive"] is True
    assert value["proposals"] == [{
        "tool": "read_record",
        "parameters": {"customer_id": "tenant-a-001", "all_tenants": True}
    }]
    assert g.judge_proposals(value["proposals"])["guard_blocked_proposals"] == 1


def test_non_tool_stop_is_valid_but_not_task_success():
    p = g.parse_chat_completion(completion(tool=None, finish="stop"))
    assert p["conclusive"] is True
    assert p["proposals"] == []


def test_length_is_inconclusive():
    p = g.parse_chat_completion(completion(tool=None, finish="length"))
    assert p["conclusive"] is False


def test_malformed_tool_json_fail_closed():
    with pytest.raises(g.EvidenceError, match="not JSON"):
        g.parse_chat_completion(completion(args="{broken"))


def test_wrong_tool_finish_is_rejected():
    with pytest.raises(g.EvidenceError, match="without function"):
        g.parse_chat_completion(completion(tool=None, finish="tool_calls"))


def test_reject_boolean_token_usage():
    body = completion()
    body["usage"]["prompt_tokens"] = True
    with pytest.raises(g.EvidenceError, match="token usage"):
        g.parse_chat_completion(body)


def test_dry_run_never_uses_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("network attempted")
    monkeypatch.setattr(g, "post_chat", forbidden)
    result = g.cli(["--model", "openai/gpt-oss-20b"])
    assert result["request_count"] == 8 and result["network_called"] is False


def test_no_credentials_never_accesses_network(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_KCC_API_KEY", raising=False)
    monkeypatch.setattr(g, "post_chat", lambda *_: (_ for _ in ()).throw(
        AssertionError("network attempted")))
    with pytest.raises(SystemExit) as exc:
        g.cli(["--execute-free", "--confirm-org-free-tier",
               "--expected-dataset-sha256", g.sha256(dataset()),
               "--result-path", str(tmp_path / "out.jsonl")])
    assert exc.value.code == 2
    assert not (tmp_path / "out.jsonl").exists()


def test_missing_free_tier_confirmation_no_api(tmp_path, monkeypatch):
    monkeypatch.setenv("GROQ_KCC_API_KEY", "FAKE_NOT_A_REAL_SECRET")
    monkeypatch.setattr(g, "post_chat", lambda *_: (_ for _ in ()).throw(
        AssertionError("network attempted")))
    with pytest.raises(SystemExit):
        g.cli(["--execute-free",
               "--expected-dataset-sha256", g.sha256(dataset()),
               "--result-path", str(tmp_path / "out.jsonl")])
    assert not (tmp_path / "out.jsonl").exists()


def test_wrong_sha_never_calls_api(tmp_path, monkeypatch):
    monkeypatch.setenv("GROQ_KCC_API_KEY", "FAKE_NOT_A_REAL_SECRET")
    monkeypatch.setattr(g, "post_chat", lambda *_: (_ for _ in ()).throw(
        AssertionError("network attempted")))
    with pytest.raises(SystemExit):
        g.cli(["--execute-free", "--confirm-org-free-tier",
               "--expected-dataset-sha256", "0" * 64,
               "--result-path", str(tmp_path / "out.jsonl")])
    assert not (tmp_path / "out.jsonl").exists()


def test_mock_transport_records_real_guard_decisions_but_no_tools(tmp_path, monkeypatch):
    p = plan(case_limit=4)
    calls = []
    def fake_chat(request_body, api_key, timeout_seconds):
        assert api_key == "FAKE_NOT_A_REAL_SECRET"
        calls.append(request_body)
        tool = "read_record" if len(calls) % 2 == 0 else "delete_record"
        return completion(tool=tool, rid=f"FAKE-ID-{len(calls)}")
    monkeypatch.setattr(g, "post_chat", fake_chat)
    monotonic_time = iter(range(100, 200, 5))
    def clock():
        return next(monotonic_time)
    destination = tmp_path / "results.jsonl"
    report = g.run_free(
        dataset(), p, api_key="FAKE_NOT_A_REAL_SECRET",
        target=destination, execute_free=True,
        confirm_org_free_tier=True, timeout_seconds=5,
        sleep_fn=lambda seconds: None, clock_fn=clock,
    )
    rows = [json.loads(x) for x in destination.read_text().splitlines()]
    assert report["recorded_responses"] == 4
    assert len(calls) == len(rows) == 4
    assert sum(row["guard"]["guard_blocked_proposals"] for row in rows) == 2
    assert sum(row["guard"]["guard_allowed_proposals"] for row in rows) == 2
    assert all(row["external_tool_dispatches"] == 0 for row in rows)
    assert all(row["free_plan_status"] == "USER_ATTESTED_NOT_PROVIDER_VERIFIED"
               for row in rows)
    # Never re-run a job into a file with existing evidence.
    with pytest.raises(g.EvidenceError, match="NEW file"):
        g.run_free(dataset(), p, api_key="FAKE_NOT_A_REAL_SECRET",
                   target=destination, execute_free=True,
                   confirm_org_free_tier=True, timeout_seconds=5,
                   sleep_fn=lambda _: None, clock_fn=clock)


def test_http_429_stops_without_automatic_retry_or_paid_fallback(monkeypatch):
    def rate_limit(*_args, **_kwargs):
        raise urllib.error.HTTPError(
            g.GROQ_ENDPOINT, 429, "Too Many Requests", {}, io.BytesIO(b"never log")
        )
    monkeypatch.setattr(g.urllib.request, "urlopen", rate_limit)
    req = g.make_chat_request(dataset()["cases"][0],
                              model="openai/gpt-oss-20b", max_completion_tokens=384)
    with pytest.raises(g.EvidenceError, match="Groq HTTP 429; STOP"):
        g.post_chat(req, "FAKE_NOT_A_REAL_SECRET", 3)
