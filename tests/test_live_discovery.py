import asyncio
import json
import sys
from pathlib import Path

from kavi_capability_compiler.discovery import DiscoveryError, discover_stdio


FIXTURE = Path(__file__).parent / "fixtures" / "live_mcp_server.py"


def test_stdio_live_discovery_builds_inventory_without_env_values():
    secret = "KCC_SHOULD_NEVER_APPEAR_IN_ARTIFACT"
    result = asyncio.run(
        discover_stdio(
            sys.executable,
            [str(FIXTURE)],
            env={"KCC_TEST_SECRET": secret},
        )
    )

    assert result["transport"] == "stdio"
    assert result["protocol_version"]
    assert result["server"]["name"] == "KCC Discovery Fixture"

    inv = result["inventory"]
    assert len(inv["capabilities"]) == 2
    by_name = {c["name"]: c for c in inv["capabilities"]}
    assert by_name["lookup_item"]["effect"] == "read"
    assert by_name["delete_item"]["effect"] == "delete"
    assert secret not in json.dumps(result)


def test_stdio_live_discovery_fails_closed_on_missing_server():
    try:
        asyncio.run(discover_stdio("__kcc_missing_executable__"))
        assert False, "expected DiscoveryError"
    except DiscoveryError as exc:
        assert "stdio discovery failed" in str(exc)
