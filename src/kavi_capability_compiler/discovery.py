from __future__ import annotations

from typing import Any, Mapping, Sequence

from mcp import Client, StdioServerParameters

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
    fallback = server_name or str(command)

    try:
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


async def discover_streamable_http(
    url: str,
    *,
    server_name: str | None = None,
) -> dict[str, Any]:
    """Discover an MCP server over Streamable HTTP using the official SDK lifecycle."""
    if not url or not str(url).startswith(("http://", "https://")):
        raise ValueError("Streamable HTTP URL must use http:// or https://")
    fallback = server_name or str(url)

    try:
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
