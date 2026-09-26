from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit


def _command_name(value: Any) -> str:
    parts = re.split(r"[\\/]", str(value or ""))
    return parts[-1] if parts else ""


def _safe_args(values: Any) -> list[str]:
    out=[]
    for value in values or []:
        text=str(value)
        if text.startswith("-"):
            out.append(text.split("=",1)[0] + ("=<redacted>" if "=" in text else ""))
        elif re.fullmatch(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}", text):
            out.append("<env-ref>")
        else:
            out.append("<arg>")
    return out


def _safe_url(value: Any) -> dict[str, Any]:
    raw=str(value or "")
    p=urlsplit(raw)
    host=p.hostname or ""
    if p.port:
        host=f"{host}:{p.port}"
    safe=urlunsplit((p.scheme,host,p.path,"",""))
    return {
        "url":safe,
        "query_keys":sorted({k for k,_ in parse_qsl(p.query,keep_blank_values=True)}),
        "had_userinfo":bool(p.username or p.password),
    }


def sanitize_mcp_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return a shareable MCP config summary that contains no secret values."""
    raw_servers=config.get("mcpServers")
    if raw_servers is None:
        raw_servers=config.get("servers")
    if not isinstance(raw_servers,dict):
        raise ValueError("MCP config must contain an mcpServers or servers object")

    servers=[]
    for name, raw in sorted(raw_servers.items()):
        if not isinstance(raw,dict):
            raise ValueError(f"Invalid MCP server config: {name}")
        url=raw.get("url") or raw.get("serverUrl")
        if url:
            safe_url=_safe_url(url)
            servers.append({
                "name":str(name),
                "transport":"streamable-http",
                **safe_url,
                "header_names":sorted(str(k) for k in (raw.get("headers") or {}).keys()),
            })
            continue
        command=raw.get("command")
        if not command:
            raise ValueError(f"MCP server {name} has neither command nor URL")
        servers.append({
            "name":str(name),
            "transport":"stdio",
            "command":_command_name(command),
            "args":_safe_args(raw.get("args")),
            "env_keys":sorted(str(k) for k in (raw.get("env") or {}).keys()),
        })
    return {"version":"kcc.mcp-config-summary.v0","servers":servers}


def runtime_server(config: dict[str, Any], name: str) -> dict[str, Any]:
    """Return the selected raw config for immediate in-memory discovery only."""
    raw_servers=config.get("mcpServers")
    if raw_servers is None:
        raw_servers=config.get("servers")
    if not isinstance(raw_servers,dict) or name not in raw_servers:
        raise KeyError(f"Unknown MCP server: {name}")
    raw=raw_servers[name]
    if not isinstance(raw,dict):
        raise ValueError(f"Invalid MCP server config: {name}")
    return dict(raw)
