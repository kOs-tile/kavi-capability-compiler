from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from .package_validator import validate_package
from .plugin_doctor import audit_inventory_readiness

MAX_FILES = 100
MAX_FILE_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024

FetchJSON = Callable[[str, Mapping[str, str]], Mapping[str, Any]]


def _github_repo_parts(repo_url: str) -> tuple[str, str]:
    parsed = urlsplit(str(repo_url))
    if parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"}:
        raise ValueError("GitHub repository URL must use https://github.com/owner/repo")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        raise ValueError("Use the repository root URL, not a nested GitHub path")
    owner, repo = parts
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not owner or not repo:
        raise ValueError("GitHub repository owner and name are required")
    return owner, repo


def _default_fetch_json(url: str, headers: Mapping[str, str]) -> Mapping[str, Any]:
    request = Request(url, headers=dict(headers))
    with urlopen(request, timeout=20) as response:
        data = response.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("GitHub API response exceeded safety limit")
    value = json.loads(data.decode("utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("Unexpected GitHub API response")
    return value


def _headers(token: str | None) -> dict[str, str]:
    out = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "kavi-plugin-doctor-v0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        out["Authorization"] = f"Bearer {token}"
    return out


def load_github_plugin_files(
    repo_url: str,
    *,
    ref: str | None = None,
    token: str | None = None,
    fetch_json: FetchJSON | None = None,
) -> dict[str, Any]:
    """Load only Plugin Doctor-relevant text files from a GitHub repository.

    Tokens are request-only and are never returned in the result.
    """

    owner, repo = _github_repo_parts(repo_url)
    fetch = fetch_json or _default_fetch_json
    headers = _headers(token)
    api_root = f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}"

    if ref is None:
        metadata = fetch(api_root, headers)
        ref = str(metadata.get("default_branch") or "")
        if not ref:
            raise ValueError("Repository default branch could not be resolved")

    tree_url = f"{api_root}/git/trees/{quote(ref, safe='')}?recursive=1"
    tree_payload = fetch(tree_url, headers)
    if tree_payload.get("truncated") is True:
        raise ValueError("Repository tree is truncated; refuse incomplete audit")

    entries = tree_payload.get("tree")
    if not isinstance(entries, list):
        raise ValueError("Repository tree response is missing entries")

    candidate_paths = []
    for entry in entries:
        if not isinstance(entry, Mapping) or entry.get("type") != "blob":
            continue
        path = str(entry.get("path") or "")
        if path in {"plugin.json", "mcp.json", ".codex-plugin/plugin.json", ".mcp.json"}:
            candidate_paths.append(path)
        elif path.startswith("skills/") and path.endswith("/SKILL.md"):
            candidate_paths.append(path)

    candidate_paths = sorted(set(candidate_paths))
    if len(candidate_paths) > MAX_FILES:
        raise ValueError("Plugin audit file count exceeds safety limit")

    files: dict[str, str] = {}
    total = 0
    for path in candidate_paths:
        content_url = f"{api_root}/contents/{quote(path, safe='/')}?ref={quote(ref, safe='')}"
        payload = fetch(content_url, headers)
        if payload.get("encoding") != "base64" or not isinstance(payload.get("content"), str):
            raise ValueError(f"Unsupported GitHub content response for {path}")
        raw = base64.b64decode(payload["content"], validate=False)
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError(f"Plugin file exceeds safety limit: {path}")
        total += len(raw)
        if total > MAX_TOTAL_BYTES:
            raise ValueError("Plugin audit input exceeds total safety limit")
        files[path] = raw.decode("utf-8")

    return {
        "source": {
            "kind": "github",
            "repository": f"https://github.com/{owner}/{repo}",
            "ref": ref,
        },
        "files": files,
    }


def load_local_plugin_files(root: str | Path) -> dict[str, Any]:
    """Read only Plugin Doctor-relevant files from a local plugin directory."""

    base = Path(root).expanduser().resolve()
    if not base.is_dir():
        raise ValueError("Local plugin root must be an existing directory")

    candidate_paths: list[Path] = []
    fixed = [
        base / "plugin.json",
        base / "mcp.json",
        base / ".codex-plugin" / "plugin.json",
        base / ".mcp.json",
    ]
    candidate_paths.extend(path for path in fixed if path.is_file())

    skills = base / "skills"
    if skills.is_dir():
        for child in sorted(skills.iterdir()):
            if child.is_dir():
                manifest = child / "SKILL.md"
                if manifest.is_file():
                    candidate_paths.append(manifest)
                for nested in child.rglob("SKILL.md"):
                    if nested != manifest and nested.is_file():
                        candidate_paths.append(nested)

    candidate_paths = sorted(set(candidate_paths))
    if len(candidate_paths) > MAX_FILES:
        raise ValueError("Plugin audit file count exceeds safety limit")

    files: dict[str, str] = {}
    total = 0
    for path in candidate_paths:
        if path.is_symlink():
            raise ValueError(f"Refuse symlinked plugin audit file: {path.name}")
        raw = path.read_bytes()
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError(f"Plugin file exceeds safety limit: {path.name}")
        total += len(raw)
        if total > MAX_TOTAL_BYTES:
            raise ValueError("Plugin audit input exceeds total safety limit")
        relative = path.relative_to(base).as_posix()
        files[relative] = raw.decode("utf-8")

    return {
        "source": {"kind": "local", "root": str(base)},
        "files": files,
    }


def audit_github_package(
    repo_url: str,
    *,
    ref: str | None = None,
    token: str | None = None,
    fetch_json: FetchJSON | None = None,
    public_submission: bool = True,
) -> dict[str, Any]:
    loaded = load_github_plugin_files(
        repo_url,
        ref=ref,
        token=token,
        fetch_json=fetch_json,
    )
    return {
        "source": loaded["source"],
        "package": validate_package(
            loaded["files"],
            public_submission=public_submission,
        ),
    }


async def audit_remote_mcp(
    url: str,
    *,
    server_name: str | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """Discover a remote MCP endpoint without invoking any discovered tool."""

    from kavi_capability_compiler.discovery import discover_streamable_http

    discovery = await discover_streamable_http(
        url,
        server_name=server_name,
        timeout_seconds=timeout_seconds,
    )
    parsed = urlsplit(url)
    safe_url = parsed._replace(query="", fragment="").geturl()

    return {
        "source": {"kind": "remote_mcp", "url": safe_url},
        "transport": discovery.get("transport"),
        "protocol_version": discovery.get("protocol_version"),
        "server": discovery.get("server"),
        "readiness": audit_inventory_readiness(discovery["inventory"]),
    }
