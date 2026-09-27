from __future__ import annotations

from typing import Any, Mapping, Sequence

import asyncio
import ipaddress
from pathlib import Path
from urllib.parse import urlsplit

import httpx2
from mcp import Client, StdioServerParameters
from mcp.client.streamable_http import streamable_http_client

from .core import scan_mcp_snapshot


class DiscoveryError(RuntimeError):
    """Live capability discovery failed before a trustworthy inventory was produced."""


def _model_dump(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return dump(by_alias=True, exclude_none=True)
    raise DiscoveryError(f"Unsupported MCP tool model: {type(value).__name__}")


def _server_identity(client: Client, fallback: str) -> tuple[str, str | None]:
    info = client.server_info
    if info is None:
        return fallback, None
    name = getattr(info, "name", None) or fallback
    version = getattr(info, "version", None)
    return str(name), str(version) if version is not None else None


def _snapshot_from_client(client: Client, tools_result: Any, fallback_name: str) -> dict[str, Any]:
    server_name, server_version = _server_identity(client, fallback_name)
    tools = [_model_dump(tool) for tool in tools_result.tools]
    return {
        "server": {"name": server_name, "version": server_version},
        "tools": tools,
    }


async def discover_stdio(
    command: str,
    args: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
    *,
    server_name: str | None = None,
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    """Discover a local MCP server over stdio and return a deterministic KCC inventory.

    Environment values are used only for the child process and are not copied into
    the returned result.
    """
    if not command or not str(command).strip():
        raise ValueError("stdio command is required")

    params = StdioServerParameters(
        command=str(command),
        args=[str(x) for x in (args or [])],
        env={str(k): str(v) for k, v in (env or {}).items()} or None,
    )
    fallback = server_name or Path(str(command)).name or "stdio-mcp"

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    try:
        async with asyncio.timeout(timeout_seconds):
            async with Client(params) as client:
                tools_result = await client.list_tools()
                snapshot = _snapshot_from_client(client, tools_result, fallback)
                inventory = scan_mcp_snapshot(snapshot)
                return {
                    "transport": "stdio",
                    "protocol_version": str(client.protocol_version),
                    "server": snapshot["server"],
                    "inventory": inventory,
                }
    except Exception as exc:
        raise DiscoveryError(f"stdio discovery failed for {fallback}: {type(exc).__name__}") from exc


def _is_loopback_host(hostname: str | None) -> bool:
    host=(hostname or "").rstrip(".").lower()
    if host=="localhost" or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _validate_streamable_http_url(url: str):
    raw=str(url)
    parsed=urlsplit(raw)
    if parsed.scheme not in {"http","https"} or not parsed.hostname:
        raise ValueError("Streamable HTTP URL must use http:// or https:// with a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Streamable HTTP URL must not contain userinfo credentials")
    if parsed.scheme=="http" and not _is_loopback_host(parsed.hostname):
        raise ValueError(
            "Plaintext HTTP discovery is allowed only for loopback hosts; "
            "use https:// for remote MCP servers"
        )
    return parsed


async def discover_streamable_http(
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    server_name: str | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """Discover an MCP server over Streamable HTTP using the official SDK lifecycle.

    Header values are used only by the HTTP client and never copied into the
    discovery artifact.
    """
    parsed = _validate_streamable_http_url(str(url))
    fallback = server_name or parsed.hostname or "http-mcp"
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    try:
        async with asyncio.timeout(timeout_seconds):
            if headers:
                async with httpx2.AsyncClient(
                    headers={str(k): str(v) for k, v in headers.items()},
                    timeout=httpx2.Timeout(30.0, read=300.0),
                ) as http_client:
                    transport = streamable_http_client(str(url), http_client=http_client)
                    async with Client(transport) as client:
                        tools_result = await client.list_tools()
                        snapshot = _snapshot_from_client(client, tools_result, fallback)
                        inventory = scan_mcp_snapshot(snapshot)
                        return {
                            "transport": "streamable-http",
                            "protocol_version": str(client.protocol_version),
                            "server": snapshot["server"],
                            "inventory": inventory,
                        }
            async with Client(str(url)) as client:
                tools_result = await client.list_tools()
                snapshot = _snapshot_from_client(client, tools_result, fallback)
                inventory = scan_mcp_snapshot(snapshot)
                return {
                    "transport": "streamable-http",
                    "protocol_version": str(client.protocol_version),
                    "server": snapshot["server"],
                    "inventory": inventory,
                }
    except Exception as exc:
        raise DiscoveryError(f"streamable HTTP discovery failed for {fallback}: {type(exc).__name__}") from exc


async def discover_config_server(config: Mapping[str, Any], name: str) -> dict[str, Any]:
    """Discover one configured MCP server without persisting raw secret values."""
    raw_servers = config.get("mcpServers")
    if raw_servers is None:
        raw_servers = config.get("servers")
    if not isinstance(raw_servers, Mapping) or name not in raw_servers:
        raise KeyError(f"Unknown MCP server: {name}")
    raw = raw_servers[name]
    if not isinstance(raw, Mapping):
        raise ValueError(f"Invalid MCP server config: {name}")

    url = raw.get("url") or raw.get("serverUrl")
    if url:
        return await discover_streamable_http(
            str(url),
            headers=raw.get("headers") if isinstance(raw.get("headers"), Mapping) else None,
            server_name=name,
        )
    command = raw.get("command")
    if not command:
        raise ValueError(f"MCP server {name} has neither command nor URL")
    args = raw.get("args")
    if args is not None and not isinstance(args, Sequence):
        raise ValueError(f"Invalid args for MCP server: {name}")
    env = raw.get("env")
    if env is not None and not isinstance(env, Mapping):
        raise ValueError(f"Invalid env for MCP server: {name}")
    return await discover_stdio(
        str(command),
        [str(x) for x in (args or [])],
        {str(k): str(v) for k, v in (env or {}).items()},
        server_name=name,
    )
