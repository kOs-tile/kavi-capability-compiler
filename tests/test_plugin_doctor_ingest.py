import base64
import json

import kavi_capability_compiler as kcc

from labs.plugin_doctor.ingest import (
    audit_github_package,
    audit_remote_mcp,
    load_github_plugin_files,
)
from labs.plugin_doctor.package_validator import PLUGIN_SCHEMA


def _b64(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def test_github_repo_loader_reads_only_plugin_surface_and_never_returns_token():
    plugin = json.dumps(
        {
            "$schema": PLUGIN_SCHEMA,
            "name": "github-fixture",
            "version": "0.1.0",
            "description": "Fixture plugin loaded through the GitHub ingestion boundary.",
        }
    )
    skill = (
        "---\n"
        "name: hello\n"
        "description: Greet users when they explicitly ask for a greeting.\n"
        "---\n\n"
        "Say hello."
    )

    def fake_fetch(url, headers):
        if url == "https://api.github.com/repos/acme/demo":
            assert headers["Authorization"] == "Bearer secret-fixture"
            return {"default_branch": "main"}
        if url == "https://api.github.com/repos/acme/demo/git/trees/main?recursive=1":
            return {
                "truncated": False,
                "tree": [
                    {"path": "plugin.json", "type": "blob"},
                    {"path": "skills/hello/SKILL.md", "type": "blob"},
                    {"path": "README.md", "type": "blob"},
                ],
            }
        if url == "https://api.github.com/repos/acme/demo/contents/plugin.json?ref=main":
            return {"encoding": "base64", "content": _b64(plugin)}
        if url == "https://api.github.com/repos/acme/demo/contents/skills/hello/SKILL.md?ref=main":
            return {"encoding": "base64", "content": _b64(skill)}
        raise AssertionError(url)

    loaded = load_github_plugin_files(
        "https://github.com/acme/demo",
        token="secret-fixture",
        fetch_json=fake_fetch,
    )

    assert sorted(loaded["files"]) == ["plugin.json", "skills/hello/SKILL.md"]
    assert "secret-fixture" not in json.dumps(loaded)

    audit = audit_github_package(
        "https://github.com/acme/demo",
        token="secret-fixture",
        fetch_json=fake_fetch,
    )
    assert audit["package"]["state"] == "SHIP"


def test_remote_mcp_ingestion_audits_discovered_inventory(monkeypatch):
    manifest = kcc.adapt_capabilities(
        "generic",
        {
            "tools": [
                {
                    "name": "read_record",
                    "description": "Read one bounded record by its stable identifier.",
                    "input_schema": {
                        "type": "object",
                        "properties": {"record_id": {"type": "string"}},
                        "required": ["record_id"],
                    },
                    "annotations": {
                        "readOnlyHint": True,
                        "destructiveHint": False,
                        "openWorldHint": False,
                    },
                }
            ]
        },
        namespace="fixture",
    )
    inventory = kcc.scan_manifest(manifest)

    async def fake_discover(url, *, server_name=None, timeout_seconds=30.0):
        assert url == "https://example.com/mcp?temporary=secret"
        return {
            "transport": "streamable-http",
            "protocol_version": "fixture",
            "server": {"name": server_name or "fixture", "version": "1"},
            "inventory": inventory,
        }

    import kavi_capability_compiler.discovery as discovery

    monkeypatch.setattr(discovery, "discover_streamable_http", fake_discover)

    import asyncio

    report = asyncio.run(
        audit_remote_mcp(
            "https://example.com/mcp?temporary=secret",
            server_name="fixture",
        )
    )

    assert report["source"]["url"] == "https://example.com/mcp"
    assert "secret" not in json.dumps(report)
    assert report["readiness"]["state"] == "SHIP"
