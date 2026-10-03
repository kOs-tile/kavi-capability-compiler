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
            "author": {"name": "KAVI Test"},
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


def test_nested_skill_manifest_is_not_discovered_as_a_skill():
    files = {
        "plugin.json": _plugin(),
        "skills/hello/nested/SKILL.md": (
            "---\nname: hello\ndescription: Say hello.\n---\nHello."
        ),
    }

    portable = validate_package(files, public_submission=False)
    directory = validate_package(files, public_submission=True)

    assert portable["state"] == "SHIP"
    assert portable["summary"]["valid_skills"] == 0
    assert directory["state"] == "BLOCKED"
    assert any(f["code"] == "PD-PKG-007" for f in directory["findings"])


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


def test_portable_profile_allows_dot_name_and_optional_submission_metadata():
    report = validate_package(
        {
            "plugin.json": json.dumps(
                {
                    "$schema": PLUGIN_SCHEMA,
                    "name": "acme.tools",
                }
            ),
            "skills/hello/SKILL.md": (
                "---\n"
                "name: hello\n"
                "description: >-\n"
                "  Greet the user when they explicitly ask\n"
                "  for a greeting.\n"
                "---\n"
                "Say hello."
            ),
        },
        public_submission=False,
    )
    assert report["state"] == "SHIP"
    assert report["summary"]["validation_profile"] == "agent_plugins_1_0"
    assert report["summary"]["valid_skills"] == 1


def test_openai_directory_profile_blocks_source_visible_submission_rules_only():
    report = validate_package(
        {
            "plugin.json": json.dumps(
                {
                    "$schema": PLUGIN_SCHEMA,
                    "name": "acme.tools",
                }
            ),
            "skills/hello/SKILL.md": (
                "---\nname: hello\ndescription: Say hello.\n---\nHello."
            ),
        },
        public_submission=True,
    )
    codes = {f["code"] for f in report["findings"]}
    assert report["state"] == "BLOCKED"
    assert report["summary"]["validation_profile"] == "openai_directory"
    assert "PD-OAI-PKG-004" in codes
    assert "PD-OAI-PKG-006" in codes
    assert "PD-PKG-005" not in codes
    assert "PD-OAI-PKG-008" not in codes
    assert report["summary"]["embedded_listing_complete"] is False
    assert report["summary"]["portal_checks_unverified"] is True


def test_repeated_rule_instances_do_not_size_bias_score():
    report = validate_package(
        {
            "plugin.json": _plugin(),
            "mcp.json": json.dumps(
                {
                    "$schema": MCP_SCHEMA,
                    "mcpServers": {
                        "one": {"type": "stdio", "command": "one"},
                        "two": {"type": "stdio", "command": "two"},
                        "three": {"type": "stdio", "command": "three"},
                    },
                }
            ),
            "skills/hello/SKILL.md": (
                "---\nname: hello\ndescription: Say hello.\n---\nHello."
            ),
        },
        public_submission=True,
    )

    assert report["state"] == "BLOCKED"
    assert report["score"] == 85
    assert report["summary"]["blockers"] == 3
    assert report["summary"]["unique_rule_codes"] == 1
    assert [f["code"] for f in report["findings"]].count("PD-MCP-007") == 3


def test_embedded_openai_listing_metadata_is_detected():
    report = validate_package(
        {
            "plugin.json": json.dumps(
                {
                    "$schema": PLUGIN_SCHEMA,
                    "name": "listing-ready",
                    "version": "1.0.0",
                    "extensions": {
                        "com.openai": {
                            "interface": {
                                "displayName": "Listing Ready",
                                "shortDescription": "A short listing subtitle",
                                "longDescription": "A longer description of what this plugin does and its limits.",
                                "developerName": "KAVI Test",
                                "category": "Developer Tools",
                            }
                        }
                    },
                }
            ),
            "skills/hello/SKILL.md": (
                "---\nname: hello\ndescription: Say hello.\n---\nHello."
            ),
        },
        public_submission=True,
    )

    assert report["state"] == "SHIP"
    assert report["summary"]["embedded_listing_complete"] is True
    assert report["summary"]["portal_checks_unverified"] is True
