from __future__ import annotations

import asyncio
import base64
import ipaddress
import os
import socket
from typing import Any
from urllib.parse import quote, urlsplit

import httpx

from doctor import audit_inventory_readiness, validate_package

MAX_FILES = 100
MAX_FILE_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024
MAX_TREE_BYTES = 8 * 1024 * 1024
MAX_MCP_CAPABILITIES = 250


def _github_parts(raw_url: str) -> tuple[str, str]:
    parsed = urlsplit(str(raw_url).strip())
    if parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"}:
        raise ValueError("Use a public repository-root URL on https://github.com.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("GitHub audit URLs must not contain credentials, query strings, or fragments.")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        raise ValueError("Use the repository root URL: https://github.com/OWNER/REPO")
    owner, repo = parts
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not owner or not repo:
        raise ValueError("GitHub owner and repository are required.")
    return owner, repo


async def _github_json(client: httpx.AsyncClient, url: str, headers: dict[str, str]) -> Any:
    response = await client.get(url, headers=headers)
    if response.status_code == 404:
        raise ValueError("Repository or plugin file was not found, or the repository is not public.")
    response.raise_for_status()
    if len(response.content) > MAX_TREE_BYTES:
        raise ValueError("GitHub response exceeded the audit safety limit.")
    return response.json()


async def audit_github(raw_url: str) -> dict[str, Any]:
    owner, repo = _github_parts(raw_url)
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "KAVI-Plugin-Doctor-V0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    api_root = f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}"
    timeout = httpx.Timeout(12.0, connect=5.0)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        metadata = await _github_json(client, api_root, headers)
        ref = str(metadata.get("default_branch") or "")
        if not ref:
            raise ValueError("Repository default branch could not be resolved.")

        tree = await _github_json(client, f"{api_root}/git/trees/{quote(ref, safe='')}?recursive=1", headers)
        if tree.get("truncated") is True:
            raise ValueError("Repository tree is truncated; Plugin Doctor refuses an incomplete audit.")

        entries = tree.get("tree")
        if not isinstance(entries, list):
            raise ValueError("Repository tree response is invalid.")

        paths: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("type") != "blob":
                continue
            path = str(entry.get("path") or "")
            if path in {"plugin.json", "mcp.json"}:
                paths.append(path)
            elif path.startswith("skills/") and path.endswith("/SKILL.md"):
                paths.append(path)

        paths = sorted(set(paths))
        if len(paths) > MAX_FILES:
            raise ValueError("Plugin audit file count exceeds the safety limit.")

        files: dict[str, str] = {}
        total = 0
        for path in paths:
            payload = await _github_json(client, f"{api_root}/contents/{quote(path, safe='/')}?ref={quote(ref, safe='')}", headers)
            if payload.get("encoding") != "base64" or not isinstance(payload.get("content"), str):
                raise ValueError(f"Unsupported GitHub content response for {path}.")
            raw = base64.b64decode(payload["content"], validate=False)
            if len(raw) > MAX_FILE_BYTES:
                raise ValueError(f"Plugin file exceeds the safety limit: {path}")
            total += len(raw)
            if total > MAX_TOTAL_BYTES:
                raise ValueError("Plugin audit input exceeds the total safety limit.")
            files[path] = raw.decode("utf-8")

    return {
        "source": {
            "kind": "github",
            "repository": f"https://github.com/{owner}/{repo}",
            "ref": ref,
        },
        "report": validate_package(files),
    }


def _assert_global_address(address: str) -> None:
    ip = ipaddress.ip_address(address)
    if not ip.is_global:
        raise ValueError("Remote MCP host resolves to a private, local, reserved, or otherwise non-global address.")


async def _validate_public_mcp_url(raw_url: str) -> tuple[str, str]:
    parsed = urlsplit(str(raw_url).strip())
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Remote MCP audit requires an HTTPS URL.")
    if parsed.username or parsed.password:
        raise ValueError("Remote MCP URL must not contain userinfo credentials.")

    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("Localhost MCP targets are not accepted by the hosted auditor.")

    try:
        _assert_global_address(host)
    except ValueError as exc:
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise exc

    loop = asyncio.get_running_loop()
    infos = await asyncio.wait_for(
        loop.run_in_executor(None, lambda: socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)),
        timeout=3.0,
    )
    addresses = {item[4][0] for item in infos}
    if not addresses:
        raise ValueError("Remote MCP hostname did not resolve.")
    for address in addresses:
        _assert_global_address(address)

    safe = parsed._replace(query="", fragment="").geturl()
    return str(raw_url).strip(), safe


async def audit_mcp(raw_url: str) -> dict[str, Any]:
    request_url, safe_url = await _validate_public_mcp_url(raw_url)

    from kavi_capability_compiler.discovery import discover_streamable_http

    try:
        discovery = await discover_streamable_http(
            request_url,
            headers={"User-Agent": "KAVI-Plugin-Doctor-V0"},
            server_name=urlsplit(request_url).hostname,
            timeout_seconds=15.0,
        )
    except Exception as exc:
        raise ValueError(f"MCP discovery failed before a trustworthy inventory was produced: {type(exc).__name__}.") from exc

    inventory = discovery.get("inventory") or {}
    capabilities = inventory.get("capabilities") or []
    if len(capabilities) > MAX_MCP_CAPABILITIES:
        raise ValueError("MCP capability count exceeds the hosted V0 safety limit.")

    return {
        "source": {
            "kind": "remote_mcp",
            "url": safe_url,
            "server": discovery.get("server"),
            "protocol_version": discovery.get("protocol_version"),
        },
        "report": audit_inventory_readiness(inventory),
    }
