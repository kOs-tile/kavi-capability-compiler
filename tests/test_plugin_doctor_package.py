import json

from labs.plugin_doctor.package_validator import (
    MCP_SCHEMA,
    PLUGIN_SCHEMA,
    validate_package,
)


def _plugin():
    return json.dumps(
        {
            "$schema": PLUGIN_SCHEMA,
            "name": "doctor-fixture",
            "version": "0.1.0",
            "description": "Fixture plugin for deterministic package validation.",
        }
    )


def test_skill_only_portable_package_can_ship():
    report = validate_package(
        {
            "plugin.json": _plugin(),
            "skills/hello/SKILL.md": (
                "---\n"
                "name: hello\n"
                "description: Greet a user when they explicitly ask for a greeting.\n"
                "---\n\n"
                "Greet the user."
            ),
        }
    )
    assert report["state"] == "SHIP"
    assert report["summary"]["valid_skills"] == 1


def test_remote_mcp_portable_package_can_ship():
    report = validate_package(
        {
            "plugin.json": _plugin(),
            "mcp.json": json.dumps(
                {
                    "$schema": MCP_SCHEMA,
                    "mcpServers": {
                        "api": {
                            "type": "streamable-http",
                            "url": "https://example.com/mcp",
                        }
                    },
                }
            ),
        }
    )
    assert report["state"] == "SHIP"
    assert report["summary"]["remote_mcp_servers"] == 1


def test_missing_plugin_manifest_is_blocked():
    report = validate_package(
        {
            "skills/hello/SKILL.md": (
                "---\nname: hello\ndescription: Say hello.\n---\nHello."
            )
        }
    )
    assert report["state"] == "BLOCKED"
    assert any(f["code"] == "PD-PKG-001" for f in report["findings"])


def test_nested_skill_manifest_is_blocked():
    report = validate_package(
        {
            "plugin.json": _plugin(),
            "skills/hello/nested/SKILL.md": (
                "---\nname: hello\ndescription: Say hello.\n---\nHello."
            ),
        }
    )
    codes = {f["code"] for f in report["findings"]}
    assert report["state"] == "BLOCKED"
    assert "PD-SKILL-005" in codes


def test_public_submission_requires_public_https_mcp():
    report = validate_package(
        {
            "plugin.json": _plugin(),
            "mcp.json": json.dumps(
                {
                    "$schema": MCP_SCHEMA,
                    "mcpServers": {
                        "local": {
                            "type": "streamable-http",
                            "url": "http://localhost:8000/mcp",
                        }
                    },
                }
            ),
        },
        public_submission=True,
    )
    assert report["state"] == "BLOCKED"
    assert any(f["code"] == "PD-MCP-006" for f in report["findings"])



def test_local_only_package_accepts_configured_stdio_mcp():
    files = {
        "plugin.json": _plugin(),
        "mcp.json": json.dumps(
            {
                "$schema": MCP_SCHEMA,
                "mcpServers": {
                    "local": {
                        "type": "stdio",
                        "command": "python",
                    }
                },
            }
        ),
    }

    local_report = validate_package(files, public_submission=False)
    public_report = validate_package(files, public_submission=True)

    assert local_report["state"] == "SHIP"
    assert local_report["summary"]["configured_mcp_servers"] == 1
    assert public_report["state"] == "BLOCKED"
    assert any(f["code"] == "PD-MCP-007" for f in public_report["findings"])
