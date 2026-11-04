"""Groq's REST transport using curl; no API key in argv, URL or filesystem.

The GitHub runner recorded 403 for keyless Python urllib but 401 for the
same keyless GET with curl. Reuse the validated curl transport for a single
request at a time. No redirects, retries, tool dispatch or paid fallback.
Credentials are delivered to curl only through a private stdin config pipe;
the subprocess arguments contain no Authorization bearer token.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import tempfile
from typing import Any

from evals.openai_responses_probe import EvidenceError, check

HOST = "https://api.groq.com"
ALLOWED_MODELS = ("openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b")
ALLOWED_URLS = frozenset(
    [HOST + "/openai/v1/chat/completions", HOST + "/openai/v1/models"] +
    [HOST + "/openai/v1/models/" + model for model in ALLOWED_MODELS]
)
KNOWN_ERROR_CODES = frozenset((
    "model_permission_blocked_org", "model_permission_blocked_project"
))
KNOWN_ERROR_TYPES = frozenset((
    "permissions_error", "authentication_error",
    "invalid_request_error", "rate_limit_error"
))


def _safe_key(key: str) -> bool:
    # Defend curl config syntax: no whitespace, quotation marks, line breaks,
    # shell metacharacters or config directives may be embedded in a key.
    # Groq gsk_ keys are ASCII tokens. Do not log their length or contents.
    return (isinstance(key, str) and 20 <= len(key) <= 512 and
            key.startswith("gsk_") and
            re.fullmatch(r"[A-Za-z0-9._~+/=-]+", key) is not None)


def classify_error(status: int, body: bytes, headers: bytes = b"") -> str:
    """Only known enums and static signatures; never echo provider text."""
    safe_type = "unclassified"
    safe_code = "unclassified"
    response_class = "unclassified"
    try:
        data = json.loads(body[:8193])
        response_class = "json"
        error = data.get("error") if isinstance(data, dict) else None
        if isinstance(error, dict):
            if error.get("type") in KNOWN_ERROR_TYPES:
                safe_type = error["type"]
            if error.get("code") in KNOWN_ERROR_CODES:
                safe_code = error["code"]
    except (ValueError, UnicodeDecodeError, TypeError):
        low = body[:16384].lower()
        response_class = (
            "cloudflare_challenge_or_1010"
            if (b"browser_signature_banned" in low or b"error 1010" in low
                or (b"cloudflare" in low and
                    (b"attention required" in low or b"blocked" in low)))
            else "html" if b"<html" in low or b"<!doctype html" in low
            else "non_json"
        )
    return (
        f"Groq HTTP {status}; error_type={safe_type}; error_code={safe_code}; "
        f"response_class={response_class}; STOP. No retry and no paid fallback."
    )


def request_json(*, method: str, url: str, key: str,
                 payload: dict[str, Any] | None = None,
                 timeout_seconds: int = 30,
                 run_fn=subprocess.run) -> dict[str, Any]:
    check(method in ("GET", "POST"), "unsupported Groq HTTP method")
    check(url in ALLOWED_URLS, "Groq endpoint not allowlisted")
    check((method == "POST") == (payload is not None),
          "POST must have payload; GET must not")
    check(method != "POST" or url == HOST + "/openai/v1/chat/completions",
          "POST restricted to chat completions")
    check(type(timeout_seconds) is int and 1 <= timeout_seconds <= 120,
          "timeout outside reviewed bound")
    check(_safe_key(key), "invalid or missing isolated GROQ_KCC_API_KEY")

    with tempfile.TemporaryDirectory(prefix="kcc-groq-curl-") as tmpdir:
        root = pathlib.Path(tmpdir)
        out = root / "response"
        header_file = root / "headers"
        args = [
            "curl", "--silent", "--show-error",
            "--max-time", str(timeout_seconds),
            "--connect-timeout", str(min(timeout_seconds, 10)),
            "--max-redirs", "0", "--retry", "0",
            "--max-filesize", "1048576",
            "--proto", "=https",
            "--config", "-",
            "--request", method,
            "--dump-header", str(header_file),
            "--output", str(out),
            "--write-out", "%{http_code}",
        ]
        if payload is not None:
            src = root / "synthetic-request.json"
            src.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
                           encoding="utf-8")
            os.chmod(src, 0o600)
            args.extend(["--header", "Content-Type: application/json",
                         "--data-binary", "@" + str(src)])
        args.append(url)

        # --config - reads from PRIVATE stdin, not argv and not a disk file.
        # Newlines and quotes in key are disallowed by _safe_key().
        config = "header = \"Authorization: Bearer " + key + "\"\n"
        try:
            completed = run_fn(
                args, input=config, text=True, capture_output=True,
                timeout=timeout_seconds + 5, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise EvidenceError("Groq curl transport failed; STOP. No retry.") from None
        # Do not print completed.stderr: it can contain untrusted provider text.
        check(completed.returncode == 0,
              "Groq curl transport failed; STOP. No retry.")
        raw_status = completed.stdout.strip()
        check(bool(re.fullmatch(r"\d{3}", raw_status)),
              "Groq curl returned invalid HTTP status")
        status = int(raw_status)
        check(100 <= status <= 599, "invalid HTTP status")
        check(out.is_file() and out.stat().st_size <= 1048576,
              "missing or oversized Groq response")
        body = out.read_bytes()
        if not 200 <= status < 300:
            headers = header_file.read_bytes()[:8192] if header_file.is_file() else b""
            raise EvidenceError(classify_error(status, body, headers))
        try:
            obj = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            raise EvidenceError("Groq returned invalid JSON; STOP.") from None
        check(isinstance(obj, dict), "Groq returned nonobject JSON")
        return obj
