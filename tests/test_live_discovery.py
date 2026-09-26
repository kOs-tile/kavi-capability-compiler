import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from kavi_capability_compiler.config import runtime_server, sanitize_mcp_config
from kavi_capability_compiler.core import diff_inventory_lock, inventory_lock
from kavi_capability_compiler.discovery import (
    DiscoveryError,
    discover_config_server,
    discover_stdio,
    discover_streamable_http,
)

FIXTURE = Path(__file__).parent / "fixtures" / "live_mcp_server.py"
HTTP_FIXTURE = Path(__file__).parent / "fixtures" / "live_mcp_http_server.py"


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_port(port, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise AssertionError("HTTP fixture did not start")


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


def test_streamable_http_live_discovery_and_header_non_persistence():
    port = _free_port()
    env = dict(os.environ)
    env["KCC_HTTP_PORT"] = str(port)
    proc = subprocess.Popen(
        [sys.executable, str(HTTP_FIXTURE)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    secret = "HTTP_SECRET_SHOULD_NOT_PERSIST"
    try:
        _wait_port(port)
        result = asyncio.run(
            discover_streamable_http(
                f"http://127.0.0.1:{port}/mcp",
                headers={"Authorization": "Bearer " + secret},
            )
        )
        assert result["transport"] == "streamable-http"
        assert result["server"]["name"] == "KCC HTTP Fixture"
        by_name = {x["name"]: x for x in result["inventory"]["capabilities"]}
        assert by_name["list_records"]["effect"] == "read"
        assert by_name["create_record"]["effect"] == "write"
        assert secret not in json.dumps(result)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)


def test_config_summary_redacts_secret_values_and_url_credentials():
    secret = "TOP_SECRET_TOKEN"
    cfg = {"mcpServers": {
        "local": {
            "command": "/usr/bin/python",
            "args": ["server.py", "--token=" + secret, "${API_KEY}"],
            "env": {"API_KEY": secret},
        },
        "remote": {
            "url": f"https://user:{secret}@example.com/mcp/{secret}?token={secret}&mode=fast",
            "headers": {"Authorization": "Bearer " + secret},
        },
    }}
    safe = sanitize_mcp_config(cfg)
    encoded = json.dumps(safe)
    assert secret not in encoded
    assert "Authorization" in encoded and "API_KEY" in encoded
    assert "token" in encoded and "mode" in encoded
    assert runtime_server(cfg, "local")["env"]["API_KEY"] == secret


def test_config_server_dispatches_stdio_without_secret_persistence():
    secret = "CONFIG_RUNTIME_SECRET"
    cfg = {"mcpServers": {
        "fixture": {
            "command": sys.executable,
            "args": [str(FIXTURE)],
            "env": {"KCC_TEST_SECRET": secret},
        }
    }}
    result = asyncio.run(discover_config_server(cfg, "fixture"))
    assert result["server"]["name"] == "KCC Discovery Fixture"
    assert secret not in json.dumps(result)


def test_live_tools_list_drift_detects_added_removed_and_changed():
    base = asyncio.run(discover_stdio(sys.executable, [str(FIXTURE)]))["inventory"]
    lock = inventory_lock(base)

    added = asyncio.run(
        discover_stdio(sys.executable, [str(FIXTURE)], env={"KCC_FIXTURE_MODE": "added"})
    )["inventory"]
    removed = asyncio.run(
        discover_stdio(sys.executable, [str(FIXTURE)], env={"KCC_FIXTURE_MODE": "removed"})
    )["inventory"]
    changed = asyncio.run(
        discover_stdio(sys.executable, [str(FIXTURE)], env={"KCC_FIXTURE_MODE": "changed"})
    )["inventory"]

    assert diff_inventory_lock(lock, added)["added"]
    assert diff_inventory_lock(lock, removed)["removed"]
    assert diff_inventory_lock(lock, changed)["changed"]


def test_cli_discover_config_writes_inventory_and_lock_without_secret(tmp_path):
    secret="CLI_SECRET_SHOULD_NOT_PERSIST"
    cfg={"mcpServers":{"fixture":{
        "command":sys.executable,
        "args":[str(FIXTURE)],
        "env":{"KCC_TEST_SECRET":secret},
    }}}
    config_path=tmp_path/"mcp.json"
    output_path=tmp_path/"discovery.json"
    lock_path=tmp_path/"inventory.lock.json"
    config_path.write_text(json.dumps(cfg))
    code="from kavi_capability_compiler import cli; cli.main()"
    proc=subprocess.run(
        [sys.executable,"-c",code,"discover-config",str(config_path),"fixture",
         "-o",str(output_path),"--lock-output",str(lock_path)],
        capture_output=True,text=True,timeout=20,
    )
    assert proc.returncode==0, proc.stderr
    discovery=json.loads(output_path.read_text())
    lock=json.loads(lock_path.read_text())
    assert discovery["server"]["name"]=="KCC Discovery Fixture"
    assert lock["inventory_digest"]==discovery["inventory"]["digest"]
    assert secret not in output_path.read_text()
    assert secret not in lock_path.read_text()


def test_stdio_discovery_timeout_is_bounded():
    hanging=Path(__file__).parent/"fixtures"/"hanging_server.py"
    started=time.monotonic()
    try:
        asyncio.run(discover_stdio(sys.executable,[str(hanging)],timeout_seconds=0.25))
        assert False, "expected DiscoveryError"
    except DiscoveryError as exc:
        assert "stdio discovery failed" in str(exc)
    assert time.monotonic()-started < 3


def test_http_failure_does_not_echo_secret_endpoint_values():
    secret="URL_SECRET_SHOULD_NOT_ECHO"
    url=f"http://127.0.0.1:1/mcp/{secret}?token={secret}"
    try:
        asyncio.run(discover_streamable_http(url,timeout_seconds=0.25))
        assert False, "expected DiscoveryError"
    except DiscoveryError as exc:
        assert secret not in str(exc)


def test_vscode_servers_and_serverurl_config_shapes_are_sanitized():
    secret="VSCODE_SECRET"
    cfg={"servers":{
        "stdio":{"command":"npx","args":["-y","pkg"],"env":{"TOKEN":secret}},
        "http":{"serverUrl":f"https://example.com/mcp/{secret}?key={secret}","headers":{"X-Token":secret}},
    }}
    safe=sanitize_mcp_config(cfg)
    encoded=json.dumps(safe)
    assert secret not in encoded
    by_name={x["name"]:x for x in safe["servers"]}
    assert by_name["stdio"]["transport"]=="stdio"
    assert by_name["http"]["transport"]=="streamable-http"
    assert by_name["http"]["origin"]=="https://example.com"
    assert by_name["http"]["path_segments"]==2
    assert by_name["http"]["query_keys"]==["key"]


def test_invalid_config_shapes_fail_closed():
    for cfg in ({}, {"mcpServers":[]}, {"mcpServers":{"bad":{}}}):
        try:
            sanitize_mcp_config(cfg)
            assert False, f"expected ValueError for {cfg}"
        except ValueError:
            pass
