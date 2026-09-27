from __future__ import annotations

import argparse
import asyncio
import copy
import json
import platform
import subprocess
import sys
import tempfile
from importlib import metadata
from pathlib import Path
from typing import Any

import kavi_capability_compiler as kcc


EXPECTED_VERSION = "0.1.0"


def dist_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def build_capsule() -> tuple[dict[str, Any], dict[str, Any], str]:
    manifest = kcc.adapt_capabilities(
        "generic",
        {
            "tools": [
                {
                    "name": "get_record",
                    "description": "Get a record",
                    "input_schema": {
                        "type": "object",
                        "properties": {"id": {"type": "string"}},
                        "required": ["id"],
                    },
                }
            ]
        },
        namespace="extras-dogfood",
    )
    inventory = kcc.scan_manifest(manifest)
    capability_id = inventory["capabilities"][0]["id"]
    capsule = kcc.compile_capsule(
        inventory,
        {
            "task": "Read one record",
            "capabilities": [capability_id],
            "ttl_seconds": 60,
        },
        {"default": "allow"},
        now=100,
    )
    return inventory, capsule, capability_id


def exercise_signing() -> dict[str, Any]:
    from kavi_capability_compiler.signing import (
        generate_ed25519_keypair,
        sign_capsule,
        verify_signed_capsule,
    )

    inventory, capsule, capability_id = build_capsule()
    private_key, public_key = generate_ed25519_keypair()
    _, wrong_public = generate_ed25519_keypair()

    envelope = sign_capsule(capsule, private_key, key_id="dogfood-root")
    valid = verify_signed_capsule(
        envelope,
        {"dogfood-root": public_key},
        now=101,
    )
    assert valid["valid"] is True

    missing_trust = verify_signed_capsule(envelope, {}, now=101)
    assert missing_trust["valid"] is False
    assert any(
        check["name"] == "trusted_key" and check["ok"] is False
        for check in missing_trust["checks"]
    )

    wrong_key = verify_signed_capsule(
        envelope,
        {"dogfood-root": wrong_public},
        now=101,
    )
    assert wrong_key["valid"] is False
    assert any(
        check["name"] == "signature" and check["ok"] is False
        for check in wrong_key["checks"]
    )

    tampered = copy.deepcopy(envelope)
    tampered["capsule"]["task"] = "tampered after signing"
    tampered_result = verify_signed_capsule(
        tampered,
        {"dogfood-root": public_key},
        now=101,
    )
    assert tampered_result["valid"] is False
    failed_tamper_checks = sorted(
        check["name"]
        for check in tampered_result["checks"]
        if check["ok"] is False
    )
    assert "envelope_integrity" in failed_tamper_checks
    assert "capsule_integrity" in failed_tamper_checks

    guard = kcc.Guard.from_signed(
        envelope,
        {"dogfood-root": public_key},
        now=101,
        inventory=inventory,
    )
    assert guard.signed is True
    assert guard.inventory_bound is True

    calls: list[dict[str, Any]] = []

    def dispatcher(params: dict[str, Any]) -> dict[str, Any]:
        calls.append(dict(params))
        return {"ok": True, "id": params["id"]}

    dispatched = guard.dispatch_sync(
        capability_id,
        dispatcher,
        parameters={"id": "123"},
        now=101,
    )
    assert dispatched["executed"] is True
    assert calls == [{"id": "123"}]

    expired = guard.authorize(
        capability_id,
        parameters={"id": "123"},
        now=1000,
    )
    assert expired["allowed"] is False
    assert expired["reason"] == "signed_capsule_invalid"

    return {
        "cryptography_version": dist_version("cryptography"),
        "valid_signature": valid["valid"],
        "missing_trust_rejected": not missing_trust["valid"],
        "wrong_key_rejected": not wrong_key["valid"],
        "tamper_rejected": not tampered_result["valid"],
        "tamper_failed_checks": failed_tamper_checks,
        "signed_guard_dispatch_count": len(calls),
        "expired_signed_guard_reason": expired["reason"],
    }


MCP_FIXTURE = r'''
from mcp.server import MCPServer

mcp = MCPServer("KCC External Extras Fixture")

@mcp.tool()
def lookup_item(query: str) -> str:
    """Search and retrieve an item without mutation."""
    return query

@mcp.tool()
def delete_item(item_id: str) -> str:
    """Delete an item permanently."""
    return item_id

if __name__ == "__main__":
    mcp.run()
'''


def exercise_mcp() -> dict[str, Any]:
    from kavi_capability_compiler.discovery import DiscoveryError, discover_stdio

    secret = "KCC_EXTERNAL_EXTRAS_SECRET_MUST_NOT_PERSIST"

    with tempfile.TemporaryDirectory(prefix="kcc-extras-") as temp_dir:
        root = Path(temp_dir)
        fixture = root / "server.py"
        config = root / "mcp.json"
        discovery_path = root / "discovery.json"
        lock_path = root / "inventory.lock.json"

        fixture.write_text(MCP_FIXTURE)
        config.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "fixture": {
                            "command": sys.executable,
                            "args": [str(fixture)],
                            "env": {
                                "KCC_TEST_SECRET": secret,
                            },
                        }
                    }
                }
            )
        )

        cli = Path(sys.executable).with_name("kcc")
        assert cli.is_file(), cli

        proc = subprocess.run(
            [
                str(cli),
                "discover-config",
                str(config),
                "fixture",
                "-o",
                str(discovery_path),
                "--lock-output",
                str(lock_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, proc.stderr

        discovery_text = discovery_path.read_text()
        lock_text = lock_path.read_text()
        assert secret not in discovery_text
        assert secret not in lock_text

        discovery = json.loads(discovery_text)
        lock = json.loads(lock_text)

        assert discovery["transport"] == "stdio"
        assert discovery["server"]["name"] == "KCC External Extras Fixture"
        assert discovery["protocol_version"]

        capabilities = {
            row["name"]: row for row in discovery["inventory"]["capabilities"]
        }
        assert set(capabilities) == {"lookup_item", "delete_item"}
        assert capabilities["lookup_item"]["effect"] == "read"
        assert capabilities["delete_item"]["effect"] == "delete"
        assert lock["inventory_digest"] == discovery["inventory"]["digest"]

        try:
            asyncio.run(discover_stdio("__kcc_missing_external_extras_binary__"))
        except DiscoveryError as exc:
            missing_binary_error = str(exc)
            assert "stdio discovery failed" in missing_binary_error
        else:
            raise AssertionError("missing MCP executable did not fail closed")

        return {
            "mcp_version": dist_version("mcp"),
            "httpx2_version": dist_version("httpx2"),
            "transport": discovery["transport"],
            "protocol_version": discovery["protocol_version"],
            "server_name": discovery["server"]["name"],
            "tool_count": len(capabilities),
            "lookup_effect": capabilities["lookup_item"]["effect"],
            "delete_effect": capabilities["delete_item"]["effect"],
            "lock_matches_inventory": (
                lock["inventory_digest"] == discovery["inventory"]["digest"]
            ),
            "secret_persisted": (
                secret in discovery_text or secret in lock_text
            ),
            "missing_binary_error": missing_binary_error,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extra", choices=("signing", "mcp", "all"), required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    assert metadata.version("kavi-capability-compiler") == EXPECTED_VERSION
    assert kcc.__version__ == EXPECTED_VERSION
    assert kcc.SDK_VERSION == "kcc.sdk.v1"

    package_path = Path(kcc.__file__).resolve()
    assert "site-packages" in package_path.parts, package_path

    result: dict[str, Any] = {
        "schema": "kcc.external-extras-dogfood.v1",
        "pass": True,
        "extra": args.extra,
        "python": platform.python_version(),
        "package_version": metadata.version("kavi-capability-compiler"),
        "sdk_version": kcc.SDK_VERSION,
        "package_path": str(package_path),
    }

    if args.extra in {"signing", "all"}:
        result["signing"] = exercise_signing()

    if args.extra in {"mcp", "all"}:
        result["mcp"] = exercise_mcp()
    else:
        # The signing extra must not pull in the MCP integration stack.
        assert dist_version("mcp") is None
        assert dist_version("httpx2") is None

    # Do not assert that the MCP-only environment lacks cryptography:
    # the MCP dependency graph may legitimately bring it transitively
    # (for example through pyjwt[crypto]). The contract under test is
    # that KCC's declared extras resolve and their public functionality works.

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
