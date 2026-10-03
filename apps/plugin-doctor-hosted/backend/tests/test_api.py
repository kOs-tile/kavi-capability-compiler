from fastapi.testclient import TestClient

import main
from main import app


def test_health_endpoint_reports_mcp_gate_off_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_REMOTE_MCP", raising=False)
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["remote_mcp_enabled"] is False
    assert response.headers["cache-control"] == "no-store"


def test_remote_mcp_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_REMOTE_MCP", raising=False)
    client = TestClient(app)
    response = client.post(
        "/api/audit",
        json={"kind": "mcp", "target": "https://example.com/mcp"},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "REMOTE_MCP_DISABLED"


def test_oversized_request_body_is_rejected_before_audit():
    client = TestClient(app)
    response = client.post(
        "/api/audit",
        content=b"x" * (main.MAX_REQUEST_BYTES + 1),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413


def test_successful_audit_gets_stable_report_fingerprint(monkeypatch):
    async def fake_github(target):
        return {
            "source": {"kind": "github", "repository": target, "ref": "main"},
            "report": {
                "state": "SHIP",
                "score": 100,
                "summary": {"findings": 0, "blockers": 0},
                "findings": [],
            },
        }

    monkeypatch.setattr(main, "audit_github", fake_github)
    client = TestClient(app)

    first = client.post(
        "/api/audit",
        json={"kind": "github", "target": "https://github.com/acme/demo"},
    )
    second = client.post(
        "/api/audit",
        json={"kind": "github", "target": "https://github.com/acme/demo"},
    )

    assert first.status_code == 200
    assert first.json()["report_fingerprint"] == second.json()["report_fingerprint"]
    assert len(first.json()["report_fingerprint"]) == 16
