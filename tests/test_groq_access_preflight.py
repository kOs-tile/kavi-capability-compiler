"""Keyless fake-transport tests for Free organization metadata diagnostics."""
from __future__ import annotations

import io
import json
import urllib.error
from unittest.mock import patch

import pytest

from evals import groq_access_preflight as p
from evals.openai_responses_probe import EvidenceError


def model_list():
    return {
        "object": "list",
        "data": [
            {"id": "openai/gpt-oss-20b", "active": True},
            {"id": "openai/gpt-oss-120b", "active": True},
            {"id": "private-model-secret", "active": True},
        ],
    }


def test_no_network_mode_is_default(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected network")
    monkeypatch.setattr(p, "get_json", forbidden)
    report = p.cli([])
    assert report["network_called"] is False
    assert report["model_completions"] == 0


def test_metadata_reads_only_two_explicit_groq_endpoints():
    sent = []
    def fake_get(url, key):
        assert key == "FAKE_TEST_KEY"
        sent.append(url)
        return model_list() if len(sent) == 1 else {
            "id": "openai/gpt-oss-20b", "active": True}
    report = p.inspect_models("FAKE_TEST_KEY", request_fn=fake_get)
    assert sent == [
        "https://api.groq.com/openai/v1/models",
        "https://api.groq.com/openai/v1/models/openai/gpt-oss-20b",
    ]
    assert report["non_inference_metadata_requests"] == 2
    assert report["catalog_contains_target"] is True
    assert report["model_detail_verified"] is True
    assert report["permissions_independently_verified"] is False
    assert report["billing_tier_independently_verified"] is False
    assert report["real_model_completions"] == 0
    assert "private-model-secret" not in json.dumps(report)


def test_model_absent_fails_closed_without_detail_request():
    sent = []
    def fake_get(url, key):
        sent.append(url)
        return {"object":"list", "data":[{"id":"llama-3.1-8b-instant"}]}
    report = p.inspect_models("FAKE_TEST_KEY", request_fn=fake_get)
    assert report["catalog_contains_target"] is False
    assert len(sent) == 1
    assert report["model_detail_verified"] is False


def test_metadata_403_org_permission_safe():
    def denied(url, key):
        raise EvidenceError("Groq HTTP 403; error_type=permissions_error; "
                            "error_code=model_permission_blocked_org; STOP.")
    with pytest.raises(EvidenceError, match="model_permission_blocked_org"):
        p.inspect_models("FAKE_TEST_KEY", request_fn=denied)


def test_metadata_request_cannot_use_arbitrary_url(monkeypatch):
    with pytest.raises(EvidenceError, match="only known"):
        p.get_json("https://attacker.invalid/steal", "FAKE_TEST_KEY")


def test_missing_metadata_key_never_contacts_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected network")
    monkeypatch.setattr(p.urllib.request, "urlopen", forbidden)
    with pytest.raises(EvidenceError, match="missing KCC-only"):
        p.get_json(p.MODELS_URL, "")


def test_model_detail_mismatch_marked_unverified():
    def fake_get(url, key):
        return model_list() if url == p.MODELS_URL else {
            "id": "other-model", "active": True}
    report = p.inspect_models("FAKE_TEST_KEY", request_fn=fake_get)
    assert report["model_detail_verified"] is False
    assert report["real_model_completions"] == 0


def test_dry_mode_does_not_accept_fake_free_confirmation():
    with pytest.raises(EvidenceError, match="confirmation"):
        p.cli(["--confirm-isolated-free-org"])


def test_explicit_live_mode_requires_confirmation(monkeypatch):
    monkeypatch.setenv("GROQ_KCC_API_KEY", "FAKE_TEST_KEY")
    with pytest.raises(EvidenceError, match="requires confirmation"):
        p.cli(["--execute-free-readonly"])


def test_403_code_extracted_from_http_error_not_body_message(monkeypatch):
    sensitive = b'{"error":{"message":"Authorization Bearer FAKE_SECRET","type":"permissions_error","code":"model_permission_blocked_project"}}'
    def forbidden(_request, *, timeout):
        raise urllib.error.HTTPError(
            p.MODELS_URL, 403, "Forbidden", {}, io.BytesIO(sensitive))
    monkeypatch.setattr(p.urllib.request, "urlopen", forbidden)
    with pytest.raises(EvidenceError, match="model_permission_blocked_project") as exc:
        p.get_json(p.MODELS_URL, "FAKE_TEST_KEY")
    assert "FAKE_SECRET" not in str(exc.value)
