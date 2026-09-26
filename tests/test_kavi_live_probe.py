import pytest

from kavi_capability_compiler.live_probe import LiveProbeError, probe_kavi_bridge


TOOLS = [
    {
        "name": "enqueue_task",
        "description": "Create one bounded task.",
        "inputSchema": {"type": "object"},
        "annotations": {"readOnlyHint": False},
    },
    {
        "name": "get_task_status",
        "description": "Read one task.",
        "inputSchema": {"type": "object"},
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "get_operator_snapshot",
        "description": "Read operator snapshot.",
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "list_recent_tasks",
        "description": "Read recent tasks.",
        "inputSchema": {"type": "object"},
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "approve_task",
        "description": "Submit approval intent.",
        "inputSchema": {"type": "object"},
        "annotations": {"readOnlyHint": False},
    },
]


class FakeTransport:
    def __init__(self):
        self.calls = []

    def __call__(self, endpoint, payload, headers, timeout):
        self.calls.append((endpoint, payload, headers, timeout))
        method = payload["method"]
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {
                    "protocolVersion": "2025-11-25",
                    "serverInfo": {
                        "name": "kavi-dispatch-bridge",
                        "version": "0.1.0",
                    },
                    "capabilities": {"tools": {}},
                },
            }
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {"tools": TOOLS},
            }
        if method == "tools/call":
            assert payload["params"]["name"] == "get_operator_snapshot"
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {
                    "content": [{"type": "text", "text": "{\"source\":\"operator_snapshot\"}"}],
                    "structuredContent": {
                        "source": "operator_snapshot",
                        "snapshot": {"state": "bounded"},
                    },
                },
            }
        raise AssertionError(method)


def test_probe_requires_secret_without_exposing_value(monkeypatch):
    monkeypatch.delenv("KAVI_DISPATCH_TOKEN", raising=False)

    with pytest.raises(LiveProbeError) as exc:
        probe_kavi_bridge("https://bridge.example/api/mcp")

    assert exc.value.code == "NEEDS_AUTH"
    assert "KAVI_DISPATCH_TOKEN" in str(exc.value)


def test_probe_uses_only_read_only_runtime_call_and_sanitizes_artifact():
    transport = FakeTransport()
    secret = "super-secret-bearer-value"

    result = probe_kavi_bridge(
        "https://user:pass@bridge.example/api/mcp?debug=secret#fragment",
        token=secret,
        now=123,
        post_json=transport,
    )

    evidence = result["evidence"]
    assert evidence["endpoint"] == "https://bridge.example/api/mcp"
    assert evidence["capability_count"] == 5
    assert evidence["snapshot_source"] == "operator_snapshot"
    assert evidence["read_only_tool_calls"] == ["get_operator_snapshot"]
    assert evidence["mutation_tool_calls"] == []
    assert evidence["secret_material_in_artifact"] is False
    assert secret not in str(result)
    assert "user:pass" not in str(result)
    assert "debug=secret" not in str(result)

    methods = [call[1]["method"] for call in transport.calls]
    assert methods == ["initialize", "tools/list", "tools/call"]
    tool_calls = [
        call[1]["params"]["name"]
        for call in transport.calls
        if call[1]["method"] == "tools/call"
    ]
    assert tool_calls == ["get_operator_snapshot"]

    for _, _, headers, _ in transport.calls:
        assert headers["Authorization"] == f"Bearer {secret}"


def test_probe_fingerprint_is_deterministic_for_same_observation():
    first = probe_kavi_bridge(
        "https://bridge.example/api/mcp",
        token="secret",
        now=123,
        post_json=FakeTransport(),
    )
    second = probe_kavi_bridge(
        "https://bridge.example/api/mcp",
        token="secret",
        now=123,
        post_json=FakeTransport(),
    )

    assert (
        first["evidence"]["report_fingerprint"]
        == second["evidence"]["report_fingerprint"]
    )
    assert first["inventory"]["digest"] == second["inventory"]["digest"]


def test_probe_rejects_non_https_endpoint_before_transport():
    with pytest.raises(LiveProbeError) as exc:
        probe_kavi_bridge(
            "http://bridge.example/api/mcp",
            token="secret",
            post_json=FakeTransport(),
        )

    assert exc.value.code == "INVALID_ENDPOINT"


def test_probe_fails_closed_on_snapshot_error():
    class BrokenSnapshot(FakeTransport):
        def __call__(self, endpoint, payload, headers, timeout):
            if payload["method"] == "tools/call":
                return {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "isError": True,
                        "structuredContent": {"error": "redacted"},
                    },
                }
            return super().__call__(endpoint, payload, headers, timeout)

    with pytest.raises(LiveProbeError) as exc:
        probe_kavi_bridge(
            "https://bridge.example/api/mcp",
            token="secret",
            post_json=BrokenSnapshot(),
        )

    assert exc.value.code == "SNAPSHOT_READ_FAILED"
