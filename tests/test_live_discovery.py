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


def _free_port():
    import socket
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        return sock.getsockname()[1]


def _wait_for_port(port, timeout=5.0):
    import socket, time
    deadline=time.time()+timeout
    while time.time()<deadline:
        with socket.socket() as sock:
            sock.settimeout(0.1)
            if sock.connect_ex(("127.0.0.1",port)) == 0:
                return
        time.sleep(0.05)
    raise AssertionError("HTTP fixture did not start")


def test_streamable_http_live_discovery_builds_inventory():
    import subprocess
    from kavi_capability_compiler.discovery import discover_streamable_http

    port=_free_port()
    proc=subprocess.Popen(
        [sys.executable,str(FIXTURE),"--http","--port",str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_port(port)
        result=asyncio.run(discover_streamable_http(f"http://127.0.0.1:{port}/mcp"))
        assert result["transport"]=="streamable-http"
        assert result["protocol_version"]
        assert result["server"]["name"]=="KCC Discovery Fixture"
        assert {c["name"] for c in result["inventory"]["capabilities"]}=={"lookup_item","delete_item"}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)


def test_live_stdio_discovery_detects_added_removed_and_changed_authority():
    from kavi_capability_compiler.core import inventory_lock, diff_inventory_lock

    base=asyncio.run(
        discover_stdio(sys.executable,[str(FIXTURE)],env={"KCC_FIXTURE_VARIANT":"base"})
    )["inventory"]
    lock=inventory_lock(base)

    drift=asyncio.run(
        discover_stdio(sys.executable,[str(FIXTURE)],env={"KCC_FIXTURE_VARIANT":"drift"})
    )["inventory"]
    diff=diff_inventory_lock(lock,drift)

    assert diff["clean"] is False
    assert diff["added"] == ["mcp:kcc-discovery-fixture:create_item"]
    assert diff["removed"] == ["mcp:kcc-discovery-fixture:delete_item"]
    assert diff["changed"] == ["mcp:kcc-discovery-fixture:lookup_item"]
