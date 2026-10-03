from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ingest import audit_github, audit_mcp

APP_VERSION = "0.0.2"
MAX_REQUEST_BYTES = 4096
MAX_CONCURRENT_AUDITS = 4
AUDIT_TIMEOUT_SECONDS = 30.0

app = FastAPI(
    title="KAVI Plugin Doctor API",
    version=APP_VERSION,
    docs_url=None,
    redoc_url=None,
)

_AUDIT_SLOTS = asyncio.Semaphore(MAX_CONCURRENT_AUDITS)


class AuditRequest(BaseModel):
    kind: Literal["github", "mcp"]
    target: str = Field(min_length=8, max_length=2048)


def _remote_mcp_enabled() -> bool:
    return os.getenv("ENABLE_REMOTE_MCP", "").strip().lower() in {"1", "true", "yes", "on"}


def _report_fingerprint(result: dict) -> str:
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


@app.middleware("http")
async def security_headers(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BYTES:
                return Response(status_code=413, content="Request body too large.")
        except ValueError:
            return Response(status_code=400, content="Invalid Content-Length.")

    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "service": "kavi-plugin-doctor",
        "version": APP_VERSION,
        "remote_mcp_enabled": _remote_mcp_enabled(),
    }


@app.post("/api/audit")
async def audit(request: AuditRequest):
    request_id = secrets.token_hex(6)

    if request.kind == "mcp" and not _remote_mcp_enabled():
        raise HTTPException(
            status_code=503,
            detail={
                "code": "REMOTE_MCP_DISABLED",
                "message": "Remote MCP auditing is disabled on this hosted deployment until hardened egress controls are enabled.",
                "request_id": request_id,
            },
        )

    try:
        async with _AUDIT_SLOTS:
            async with asyncio.timeout(AUDIT_TIMEOUT_SECONDS):
                if request.kind == "github":
                    result = await audit_github(request.target)
                else:
                    result = await audit_mcp(request.target)

        return {
            "request_id": request_id,
            "report_fingerprint": _report_fingerprint(result),
            **result,
        }
    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail={
                "code": "AUDIT_TIMEOUT",
                "message": "The audit exceeded the hosted execution budget.",
                "request_id": request_id,
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "AUDIT_REJECTED", "message": str(exc), "request_id": request_id},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "AUDIT_UPSTREAM_FAILURE",
                "message": "The audit could not complete against the upstream target.",
                "request_id": request_id,
            },
        ) from exc
