import json
import sys

import pytest

from kavi_capability_compiler.cli import main
from kavi_capability_compiler.core import compile_capsule, digest, scan_mcp_snapshot


def _write(path, value):
    path.write_text(json.dumps(value))


def _capsule():
    inventory = scan_mcp_snapshot({
        "server": {"name": "demo"},
        "tools": [{
            "name": "search_code",
            "description": "Search code",
            "inputSchema": {"type": "object"},
        }],
    })
    return compile_capsule(
        inventory,
        {"task": "search", "capabilities": ["mcp:demo:search_code"]},
        {"default": "allow"},
        now=100,
    )


def test_evidence_bind_cli_writes_valid_envelope(tmp_path, monkeypatch):
    capsule = _capsule()
    capsule_path = tmp_path / "capsule.json"
    evidence_path = tmp_path / "evidence.json"
    output_path = tmp_path / "execution-evidence.json"
    _write(capsule_path, capsule)
    _write(evidence_path, [
        {
            "kind": "context",
            "producer": "oracle",
            "artifact_id": "state-1",
            "artifact_digest": digest({"trusted": True}),
        }
    ])

    monkeypatch.setattr(sys, "argv", [
        "kcc",
        "evidence-bind",
        str(capsule_path),
        "--execution-id", "exec-1",
        "--evidence", str(evidence_path),
        "--capability", "mcp:demo:search_code",
        "--operation", "search",
        "-o", str(output_path),
    ])
    main()

    envelope = json.loads(output_path.read_text())
    assert envelope["capsule_id"] == capsule["capsule_id"]
    assert envelope["execution_id"] == "exec-1"
    assert envelope["authority_granted"] is False
    assert len(envelope["evidence"]) == 1


def test_evidence_verify_cli_success(tmp_path, monkeypatch, capsys):
    capsule = _capsule()
    capsule_path = tmp_path / "capsule.json"
    evidence_path = tmp_path / "refs.json"
    envelope_path = tmp_path / "envelope.json"
    _write(capsule_path, capsule)
    _write(evidence_path, [
        {
            "kind": "memory",
            "producer": "mnemos",
            "artifact_id": "query-1",
            "artifact_digest": digest({"policy_leak_count": 0}),
        }
    ])

    monkeypatch.setattr(sys, "argv", [
        "kcc", "evidence-bind", str(capsule_path),
        "--execution-id", "exec-1",
        "--evidence", str(evidence_path),
        "-o", str(envelope_path),
    ])
    main()

    monkeypatch.setattr(sys, "argv", [
        "kcc", "evidence-verify", str(envelope_path),
    ])
    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True


def test_evidence_verify_cli_fails_on_tamper(tmp_path, monkeypatch, capsys):
    capsule = _capsule()
    envelope = {
        "version": "kavi.execution-evidence.v0",
        "execution_id": "exec-1",
        "capsule_id": capsule["capsule_id"],
        "capability_id": None,
        "operation": None,
        "evidence": [],
        "authority_granted": False,
        "authority_note": "tampered",
        "digest": "0" * 64,
    }
    path = tmp_path / "bad.json"
    _write(path, envelope)

    monkeypatch.setattr(sys, "argv", ["kcc", "evidence-verify", str(path)])
    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 4
    assert json.loads(capsys.readouterr().out)["valid"] is False
