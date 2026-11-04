"""Keyless tests of curl transport. All subprocesses mocked, no network."""
from __future__ import annotations
import json
import os
import pathlib
import subprocess

import pytest

from evals import groq_curl_transport as t
from evals.openai_responses_probe import EvidenceError

KEY = "gsk_FAKE_ONLY_A_TEST_NOT_REAL_12345"
URL = t.HOST + "/openai/v1/models"
CHAT = t.HOST + "/openai/v1/chat/completions"


def fake_runner(status, body, seen):
    def run(args, *, input, text, capture_output, timeout, check):
        assert args[0] == "curl"
        assert text is True and capture_output is True and check is False
        assert input == f'header = "Authorization: Bearer {KEY}"\n'
        assert KEY not in repr(args)
        assert "--config" in args and args[args.index("--config") + 1] == "-"
        assert args[args.index("--retry") + 1] == "0"
        assert "--location" not in args
        assert args[args.index("--max-redirs") + 1] == "0"
        assert args[args.index("--proto") + 1] == "=https"
        outfile = pathlib.Path(args[args.index("--output") + 1])
        outfile.write_bytes(body)
        pathlib.Path(args[args.index("--dump-header") + 1]).write_bytes(
            b"HTTP/2 " + str(status).encode() + b"\nserver: cloudflare\n")
        seen.append({"args": list(args), "input_is_private": True})
        return subprocess.CompletedProcess(args, 0, stdout=str(status), stderr="")
    return run


def test_keyless_mock_curl_metadata_success():
    seen = []
    response = {"object": "list", "data": [{"id": "openai/gpt-oss-20b"}]}
    obj = t.request_json(
        method="GET", url=URL, key=KEY,
        run_fn=fake_runner(200, json.dumps(response).encode(), seen))
    assert obj == response
    assert len(seen) == 1


def test_secret_in_private_stdin_never_in_arguments_or_payload():
    seen = []
    payload = {"model": "openai/gpt-oss-20b", "messages": [
        {"role": "user", "content": "synthetic only"}]}
    def run(args, **kwargs):
        request_file = pathlib.Path(
            args[args.index("--data-binary") + 1].removeprefix("@"))
        assert request_file.is_file()
        assert os.stat(request_file).st_mode & 0o077 == 0
        body = request_file.read_text()
        assert json.loads(body) == payload
        assert KEY not in body
        assert KEY not in repr(args)
        return fake_runner(200, b'{"id":"fake"}', seen)(args, **kwargs)
    result = t.request_json(
        method="POST", url=CHAT, key=KEY, payload=payload, run_fn=run)
    assert result["id"] == "fake"
    assert len(seen) == 1


def test_json_403_captures_only_allowlisted_code():
    seen = []
    body = b'{"error":{"type":"permissions_error","code":"model_permission_blocked_project","message":"Authorization Bearer MUST_NOT_LEAK"}}'
    with pytest.raises(EvidenceError, match="error_code=model_permission_blocked_project") as e:
        t.request_json(method="GET", url=URL, key=KEY,
                       run_fn=fake_runner(403, body, seen))
    assert len(seen) == 1
    assert "MUST_NOT_LEAK" not in str(e.value)


def test_html_403_classifies_cloudflare_without_raw_body():
    body = b'<html><head>Cloudflare</head><body>Attention Required: blocked - PRIVATE_TOKEN_abc</body></html>'
    with pytest.raises(EvidenceError, match="response_class=cloudflare_challenge_or_1010") as e:
        t.request_json(method="GET", url=URL, key=KEY,
                       run_fn=fake_runner(403, body, []))
    assert "PRIVATE_TOKEN" not in str(e.value)


def test_http_401_stops_with_no_retry():
    seen = []
    with pytest.raises(EvidenceError, match="Groq HTTP 401"):
        t.request_json(method="GET", url=URL, key=KEY,
                       run_fn=fake_runner(401, b'{"error":"unauthorized"}', seen))
    assert len(seen) == 1


def test_invalid_key_with_quote_or_newline_blocks_before_subprocess():
    for key in ["", "FAKE_NOT_A_GROQ_KEY", "gsk_test\"injected\nheader=other",
                "gsk_abc;curlconfiginjection000", "gsk_shrt"]:
        def forbidden(*_args, **_kwargs):
            raise AssertionError("curl should not execute")
        with pytest.raises(EvidenceError, match="invalid or missing"):
            t.request_json(method="GET", url=URL, key=key, run_fn=forbidden)


def test_endpoint_allowlist_blocks_exfiltration_and_unreviewed_post():
    def forbidden(*_args, **_kwargs):
        raise AssertionError("curl should not execute")
    with pytest.raises(EvidenceError, match="not allowlisted"):
        t.request_json(method="GET", url="https://evil.invalid/", key=KEY,
                       run_fn=forbidden)
    with pytest.raises(EvidenceError, match="restricted to chat completions"):
        t.request_json(method="POST", url=URL, key=KEY,
                       payload={"synthetic": True}, run_fn=forbidden)


def test_no_redirect_even_if_provider_returns_302():
    with pytest.raises(EvidenceError, match="Groq HTTP 302"):
        t.request_json(method="GET", url=URL, key=KEY,
                       run_fn=fake_runner(302, b"", []))


def test_curl_failure_never_leaks_stderr_or_retries():
    calls = []
    def failed(args, **kwargs):
        calls.append(1)
        return subprocess.CompletedProcess(
            args, 60, stdout="000", stderr="Authorization Bearer SECRET")
    with pytest.raises(EvidenceError, match="transport failed") as e:
        t.request_json(method="GET", url=URL, key=KEY, run_fn=failed)
    assert len(calls) == 1
    assert "SECRET" not in str(e.value)


def test_curl_fake_response_invalid_json_stops():
    with pytest.raises(EvidenceError, match="invalid JSON"):
        t.request_json(method="GET", url=URL, key=KEY,
                       run_fn=fake_runner(200, b"not json", []))
