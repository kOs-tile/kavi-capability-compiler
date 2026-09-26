import asyncio
import json
import sys
import os
import socket
import subprocess
import time
from pathlib import Path

from kavi_capability_compiler.discovery import DiscoveryError, discover_stdio, discover_streamable_http
from kavi_capability_compiler.config import sanitize_mcp_config, runtime_server


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


HTTP_FIXTURE = Path(__file__).parent / "fixtures" / "live_mcp_http_server.py"


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1",0))
        return s.getsockname()[1]


def _wait_port(port, timeout=5):
    deadline=time.time()+timeout
    while time.time()<deadline:
        try:
            with socket.create_connection(("127.0.0.1",port),timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise AssertionError("HTTP fixture did not start")


def test_streamable_http_live_discovery_builds_inventory():
    port=_free_port()
    env=dict(os.environ); env["KCC_HTTP_PORT"]=str(port)
    proc=subprocess.Popen([sys.executable,str(HTTP_FIXTURE)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        _wait_port(port)
        result=asyncio.run(discover_streamable_http(f"http://127.0.0.1:{port}/mcp"))
        assert result["transport"]=="streamable-http"
        assert result["server"]["name"]=="KCC HTTP Fixture"
        by_name={x["name"]:x for x in result["inventory"]["capabilities"]}
        assert by_name["list_records"]["effect"]=="read"
        assert by_name["create_record"]["effect"]=="write"
    finally:
        proc.terminate()
        try: proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait(timeout=3)


def test_config_summary_redacts_secret_values_and_url_credentials():
    secret="TOP_SECRET_TOKEN"
    cfg={"mcpServers":{
        "local":{"command":"/usr/bin/python","args":["server.py","--token="+secret,"${API_KEY}"],"env":{"API_KEY":secret}},
        "remote":{"url":f"https://user:{secret}@example.com/mcp?token={secret}&mode=fast","headers":{"Authorization":"Bearer "+secret}}
    }}
    safe=sanitize_mcp_config(cfg)
    encoded=json.dumps(safe)
    assert secret not in encoded
    assert "Authorization" in encoded and "API_KEY" in encoded
    assert "token" in encoded and "mode" in encoded
    assert runtime_server(cfg,"local")["env"]["API_KEY"]==secret
