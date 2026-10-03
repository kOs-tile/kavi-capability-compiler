import json

from doctor import PLUGIN_SCHEMA, audit_inventory_readiness, validate_package
from kavi_capability_compiler.core import scan_mcp_snapshot


def test_clean_skill_package_ships():
    report = validate_package(
        {
            "plugin.json": json.dumps(
                {
                    "$schema": PLUGIN_SCHEMA,
                    "name": "clean-plugin",
                    "version": "0.1.0",
                    "description": "A clean portable plugin fixture for hosted Plugin Doctor.",
                }
            ),
            "skills/hello/SKILL.md": (
                "---\n"
                "name: hello\n"
                "description: Greet a user when they explicitly ask for a greeting.\n"
                "---\n"
                "Say hello."
            ),
        }
    )
    assert report["state"] == "SHIP"
    assert report["score"] == 100
    assert report["summary"]["blockers"] == 0


def test_malformed_package_fails_closed():
    report = validate_package(
        {
            "skills/broken/SKILL.md": "---\nname: broken\n",
        }
    )
    assert report["state"] == "BLOCKED"
    codes = {row["code"] for row in report["findings"]}
    assert "PD-PKG-001" in codes
    assert "PD-SKILL-003" in codes


def test_read_only_inventory_can_ship_when_metadata_is_explicit():
    inventory = scan_mcp_snapshot(
        {
            "server": {"name": "fixture"},
            "tools": [
                {
                    "name": "read_record",
                    "description": "Read one record by its stable record identifier.",
                    "inputSchema": {
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
            ],
        }
    )
    report = audit_inventory_readiness(inventory)
    assert report["state"] == "SHIP"
    assert report["score"] == 100


def test_unknown_authority_is_blocked():
    inventory = scan_mcp_snapshot(
        {
            "server": {"name": "fixture"},
            "tools": [
                {
                    "name": "process",
                    "description": "Process the selected object with configured behavior.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"id": {"type": "string"}},
                    },
                    "annotations": {
                        "readOnlyHint": False,
                        "destructiveHint": False,
                        "openWorldHint": False,
                    },
                }
            ],
        }
    )
    report = audit_inventory_readiness(inventory)
    assert report["state"] == "BLOCKED"
    assert any(row["code"] == "PD-S001" for row in report["findings"])
