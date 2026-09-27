"""Sanitized live probe for the KAVI Dispatch Bridge.

The bearer credential is consumed only from memory for authenticated transport.
It is never returned, hashed into evidence, or included in exception messages.
The probe invokes only MCP initialize, tools/list, and the read-only
get_operator_snapshot tool.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from kavi_capability_compiler.core import digest, scan_mcp_snapshot


PROTOCOL_VERSION = "2025-11-25"


class LiveProbeError(RuntimeError):
    """Sanitized live-probe failure."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _safe_endpoint(endpoint: str) -> str:
    parts = urlsplit(str(endpoint).strip())
    if parts.scheme != "https":
        raise LiveProbeError("INVALID_ENDPOINT", "KAVI live probe requires HTTPS")
    if not parts.hostname:
        raise LiveProbeError("INVALID_ENDPOINT", "KAVI live probe requires a valid host")
    host = parts.hostname
    if parts.port:
        host = f"{host}:{parts.port}"
    path = parts.path or "/api/mcp"
    return urlunsplit(("https", host, path, "", ""))


def _default_post_json(
    endpoint: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = Request(endpoint, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            if response.status != 200:
                raise LiveProbeError(
                    "HTTP_ERROR",
                    f"KAVI bridge returned HTTP {response.status}",
                )
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise LiveProbeError("AUTH_REJECTED", "KAVI bridge rejected probe authentication")
        raise LiveProbeError("HTTP_ERROR", f"KAVI bridge returned HTTP {exc.code}")
    except URLError as exc:
        raise LiveProbeError("NETWORK_ERROR", "KAVI bridge could not be reached") from exc
    except TimeoutError as exc:
        raise LiveProbeError("TIMEOUT", "KAVI bridge probe timed out") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LiveProbeError("INVALID_JSON", "KAVI bridge returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise LiveProbeError("INVALID_RESPONSE", "KAVI bridge returned a non-object response")
    return parsed


def _rpc_result(response: dict[str, Any], expected_id: int) -> dict[str, Any]:
    if response.get("id") != expected_id:
        raise LiveProbeError("RPC_ID_MISMATCH", "KAVI bridge returned an unexpected RPC id")
    if response.get("error"):
        raise LiveProbeError("RPC_ERROR", "KAVI bridge returned a JSON-RPC error")
    result = response.get("result")
    if not isinstance(result, dict):
        raise LiveProbeError("RPC_RESULT_MISSING", "KAVI bridge response did not contain a result")
    return result


def probe_kavi_bridge(
    endpoint: str,
    *,
    token: str | None = None,
    token_env: str = "KAVI_DISPATCH_TOKEN",
    timeout: float = 10.0,
    now: int | None = None,
    post_json: Callable[
        [str, dict[str, Any], dict[str, str], float],
        dict[str, Any],
    ] | None = None,
) -> dict[str, Any]:
    """Observe the live read-only bridge surface and return sanitized evidence."""
    safe_endpoint = _safe_endpoint(endpoint)
    credential = token if token is not None else os.getenv(token_env)
    if not credential:
        raise LiveProbeError(
            "NEEDS_AUTH",
            f"Authenticated KAVI bridge probe requires {token_env} in a secure environment",
        )

    transport = post_json or _default_post_json
    headers = {
        "Authorization": f"Bearer {credential}",
        "Content-Type": "application/json",
        "MCP-Protocol-Version": PROTOCOL_VERSION,
        "User-Agent": "kavi-capability-compiler-live-probe/0.1",
    }

    initialize = transport(
        safe_endpoint,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "kavi-capability-compiler",
                    "version": "0.0.1",
                },
            },
        },
        headers,
        timeout,
    )
    init_result = _rpc_result(initialize, 1)
    server_info = init_result.get("serverInfo") or {}
    protocol_version = init_result.get("protocolVersion")

    listed = transport(
        safe_endpoint,
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        headers,
        timeout,
    )
    tools_result = _rpc_result(listed, 2)
    tools = tools_result.get("tools")
    if not isinstance(tools, list) or not tools:
        raise LiveProbeError("TOOLS_MISSING", "KAVI bridge returned no tools")

    server_name = str(server_info.get("name") or "kavi-dispatch-bridge")
    inventory = scan_mcp_snapshot({
        "server": {"name": server_name},
        "tools": tools,
    })

    snapshot_response = transport(
        safe_endpoint,
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_operator_snapshot",
                "arguments": {},
            },
        },
        headers,
        timeout,
    )
    snapshot_result = _rpc_result(snapshot_response, 3)
    if snapshot_result.get("isError") is True:
        raise LiveProbeError(
            "SNAPSHOT_READ_FAILED",
            "KAVI bridge read-only operator snapshot call failed",
        )
    structured = snapshot_result.get("structuredContent")
    if not isinstance(structured, dict):
        raise LiveProbeError(
            "SNAPSHOT_MISSING",
            "KAVI bridge did not return structured operator snapshot evidence",
        )

    observed_at = int(now if now is not None else time.time())
    evidence: dict[str, Any] = {
        "version": "kcc.kavi-live-probe.v0",
        "endpoint": safe_endpoint,
        "observed_at": observed_at,
        "authentication": "bearer_in_memory",
        "protocol_version": protocol_version,
        "server_info": {
            "name": server_info.get("name"),
            "version": server_info.get("version"),
        },
        "inventory_digest": inventory["digest"],
        "capability_count": len(inventory["capabilities"]),
        "capability_ids": sorted(item["id"] for item in inventory["capabilities"]),
        "tool_names": sorted(item["name"] for item in inventory["capabilities"]),
        "snapshot_source": structured.get("source"),
        "snapshot_digest": digest(structured),
        "read_only_tool_calls": ["get_operator_snapshot"],
        "mutation_tool_calls": [],
        "secret_material_in_artifact": False,
    }
    evidence["report_fingerprint"] = digest(evidence)
    evidence_reference = {
        "kind": "runtime_authority_surface",
        "producer": "kcc-kavi-live-probe",
        "artifact_id": (
            f"{server_info.get('name') or 'kavi-dispatch-bridge'}:"
            f"{observed_at}"
        ),
        "artifact_digest": evidence["report_fingerprint"],
    }

    return {
        "inventory": inventory,
        "evidence": evidence,
        "evidence_ref": evidence_reference,
    }
