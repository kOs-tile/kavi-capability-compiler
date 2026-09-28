from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from importlib import metadata
from pathlib import Path

import kavi_capability_compiler as kcc


EXPECTED_SCHEMAS = (
    "kcc.capabilities.v1",
    "kcc.capsule.v1",
    "kcc.inventory-lock.v1",
    "kcc.inventory.v1",
    "kcc.signed-capsule.v1",
)


def payload(source_format: str):
    generic_tools = {
        "tools": [
            {
                "name": "get_record",
                "description": "Get a record by ID",
                "input_schema": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                    "required": ["id"],
                },
            },
            {
                "name": "update_record",
                "description": "Update a record",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["id", "value"],
                },
            },
        ]
    }

    if source_format in {"generic", "anthropic"}:
        return generic_tools

    if source_format == "openai":
        return {
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"],
                    },
                }
                for tool in generic_tools["tools"]
            ]
        }

    if source_format == "mcp":
        return {
            "tools": [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "inputSchema": tool["input_schema"],
                }
                for tool in generic_tools["tools"]
            ]
        }

    if source_format == "openapi":
        return {
            "openapi": "3.1.0",
            "paths": {
                "/records/get": {
                    "post": {
                        "operationId": "get_record",
                        "description": "Get a record by ID",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": generic_tools["tools"][0]["input_schema"]
                                }
                            }
                        },
                    }
                },
                "/records/update": {
                    "post": {
                        "operationId": "update_record",
                        "description": "Update a record",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": generic_tools["tools"][1]["input_schema"]
                                }
                            }
                        },
                    }
                },
            },
        }

    raise AssertionError(f"unsupported dogfood format: {source_format}")


def exercise(source_format: str) -> dict[str, object]:
    kwargs = {"namespace": f"dogfood-{source_format}"}
    if source_format == "mcp":
        kwargs["server"] = "dogfood-server"

    manifest = kcc.adapt_capabilities(source_format, payload(source_format), **kwargs)
    inventory = kcc.scan_manifest(manifest)
    ids = {item["name"]: item["id"] for item in inventory["capabilities"]}
    read_id = ids["get_record"]
    update_id = ids["update_record"]

    capsule = kcc.compile_capsule(
        inventory,
        {
            "task": "Read one record without mutation",
            "capabilities": [read_id],
            "capability_constraints": {
                read_id: {"parameters": {"id": "123"}},
            },
        },
        {"default": "allow"},
        now=100,
    )
    guard = kcc.Guard.from_capsule(capsule, inventory=inventory)
    assert guard.inventory_bound is True

    read_calls: list[dict[str, str]] = []

    def read_dispatcher(params):
        read_calls.append(dict(params))
        return {"id": params["id"], "value": "external-dogfood"}

    result = guard.dispatch_sync(
        read_id,
        read_dispatcher,
        parameters={"id": "123"},
        now=101,
    )
    assert result["executed"] is True
    assert result["result"] == {"id": "123", "value": "external-dogfood"}
    assert read_calls == [{"id": "123"}]

    mutation_calls: list[dict[str, str]] = []

    def mutation_dispatcher(params):
        mutation_calls.append(dict(params))
        return {"updated": True}

    try:
        guard.dispatch_sync(
            update_id,
            mutation_dispatcher,
            parameters={"id": "123", "value": "must-not-run"},
            now=101,
        )
    except kcc.AuthorityDenied as exc:
        reason = getattr(exc, "reason", None)
        if reason is None:
            reason = exc.decision["reason"]
    else:
        raise AssertionError("out-of-capsule mutation reached dispatcher")

    assert reason == "capability_not_granted"
    assert mutation_calls == []

    return {
        "source_format": source_format,
        "manifest_version": manifest["schema_version"],
        "inventory_version": inventory["version"],
        "capsule_version": capsule["version"],
        "read_dispatch_count": len(read_calls),
        "denied_mutation_dispatch_count": len(mutation_calls),
        "denial_reason": reason,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--distribution", required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    installed_version = metadata.version("kavi-capability-compiler")
    assert installed_version == args.expected_version
    assert kcc.__version__ == args.expected_version
    assert kcc.SDK_VERSION == "kcc.sdk.v1"
    assert kcc.schema_names() == EXPECTED_SCHEMAS

    for name in EXPECTED_SCHEMAS:
        assert isinstance(kcc.get_schema(name), dict)

    package_path = Path(kcc.__file__).resolve()
    assert "site-packages" in package_path.parts, package_path

    cli_executable = Path(sys.executable).with_name("kcc")
    assert cli_executable.is_file(), cli_executable
    cli = subprocess.run(
        [str(cli_executable), "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert cli == args.expected_version

    formats = ("generic", "openai", "anthropic", "mcp", "openapi")
    results = [exercise(source_format) for source_format in formats]

    evidence = {
        "schema": "kcc.external-consumer-dogfood.v1",
        "pass": True,
        "distribution": args.distribution,
        "python": platform.python_version(),
        "package_version": installed_version,
        "sdk_version": kcc.SDK_VERSION,
        "cli_version": cli,
        "package_path": str(package_path),
        "schemas": list(kcc.schema_names()),
        "formats": results,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
