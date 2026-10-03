from __future__ import annotations

import secrets
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ingest import audit_github, audit_mcp

app = FastAPI(
    title="KAVI Plugin Doctor API",
    version="0.0.1",
    docs_url=None,
    redoc_url=None,
)


class AuditRequest(BaseModel):
    kind: Literal["github", "mcp"]
    target: str = Field(min_length=8, max_length=2048)


@app.get("/api/health")
async def health():
    return {"ok": True, "service": "kavi-plugin-doctor", "version": "0.0.1"}


@app.post("/api/audit")
async def audit(request: AuditRequest):
    request_id = secrets.token_hex(6)
    try:
        if request.kind == "github":
            result = await audit_github(request.target)
        else:
            result = await audit_mcp(request.target)
        return {"request_id": request_id, **result}
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
