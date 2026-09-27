from __future__ import annotations

import argparse
import copy
import json
import platform
from importlib import metadata
from pathlib import Path
from typing import Any

import kavi_capability_compiler as kcc


def inventory(*, drift: bool = False) -> dict[str, Any]:
    description = "Get a record by ID" if not drift else "Get a record by ID from the current source"
    manifest = kcc.adapt_capabilities(
        "generic",
        {
            "tools": [
                {
                    "name": "get_record",
                    "description": description,
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "extra": {"type": "string"},
                        },
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
        },
        namespace="diagnostics-dogfood",
    )
    return kcc.scan_manifest(manifest)


def ids(inv: dict[str, Any]) -> dict[str, str]:
    return {row["name"]: row["id"] for row in inv["capabilities"]}


def compile_for(
    inv: dict[str, Any],
    capability_id: str,
    *,
    policy: dict[str, Any],
    constraints: dict[str, Any] | None = None,
    ttl_seconds: int = 900,
) -> dict[str, Any]:
    intent: dict[str, Any] = {
        "task": "diagnostics dogfood",
        "capabilities": [capability_id],
        "ttl_seconds": ttl_seconds,
    }
    if constraints is not None:
        intent["capability_constraints"] = {capability_id: constraints}
    return kcc.compile_capsule(inv, intent, policy, now=100)


def denied_case(
    name: str,
    guard: kcc.Guard,
    capability_id: str,
    *,
    expected_exception: type[BaseException],
    expected_reason: str,
    operation: str | None = None,
    parameters: dict[str, Any] | None = None,
    now: int = 101,
    expected_failed_checks: set[str] | None = None,
) -> dict[str, Any]:
    calls: list[dict[str, Any]] = []

    def dispatcher(params: dict[str, Any]) -> dict[str, Any]:
        calls.append(dict(params))
        return {"unexpected": True}

    try:
        guard.dispatch_sync(
            capability_id,
            dispatcher,
            operation=operation,
            parameters=parameters,
            now=now,
        )
    except expected_exception as exc:
        if type(exc) is not expected_exception:
            raise AssertionError(
                f"{name}: expected exact {expected_exception.__name__}, got {type(exc).__name__}"
            )
        reason = getattr(exc, "reason", None)
        decision = getattr(exc, "decision", None)
        assert isinstance(decision, dict), f"{name}: missing structured .decision"
        assert reason == expected_reason, f"{name}: {reason!r} != {expected_reason!r}"
        assert str(exc) == expected_reason, f"{name}: exception message drift"
        assert decision.get("allowed") is False, f"{name}: denial not explicit"
        assert calls == [], f"{name}: denied call reached dispatcher"

        failed_checks: list[str] = []
        verification = decision.get("verification")
        if verification is not None:
            assert isinstance(verification, dict), f"{name}: invalid verification payload"
            failed_checks = sorted(
                check["name"]
                for check in verification.get("checks", [])
                if check.get("ok") is False
            )

        if expected_failed_checks is not None:
            assert expected_failed_checks.issubset(set(failed_checks)), (
                f"{name}: expected failed checks {sorted(expected_failed_checks)}, "
                f"got {failed_checks}"
            )

        return {
            "case": name,
            "exception": type(exc).__name__,
            "reason": reason,
            "dispatcher_calls": len(calls),
            "failed_checks": failed_checks,
            "decision_keys": sorted(decision),
        }
    except BaseException as exc:
        raise AssertionError(
            f"{name}: expected {expected_exception.__name__}, got {type(exc).__name__}: {exc}"
        ) from exc
    raise AssertionError(f"{name}: denial did not raise")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--distribution", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    assert metadata.version("kavi-capability-compiler") == "0.1.0"
    assert kcc.__version__ == "0.1.0"
    assert kcc.SDK_VERSION == "kcc.sdk.v1"
    package_path = Path(kcc.__file__).resolve()
    assert "site-packages" in package_path.parts, package_path

    inv = inventory()
    capability_ids = ids(inv)
    read_id = capability_ids["get_record"]
    update_id = capability_ids["update_record"]

    cases: list[dict[str, Any]] = []

    read_only_capsule = compile_for(
        inv,
        read_id,
        policy={"default": "allow"},
    )
    cases.append(
        denied_case(
            "capability_not_granted",
            kcc.Guard.from_capsule(read_only_capsule, inventory=inv),
            update_id,
            expected_exception=kcc.AuthorityDenied,
            expected_reason="capability_not_granted",
        )
    )

    denied_capsule = compile_for(
        inv,
        update_id,
        policy={"default": "deny"},
    )
    cases.append(
        denied_case(
            "explicit_policy_denial",
            kcc.Guard.from_capsule(denied_capsule, inventory=inv),
            update_id,
            expected_exception=kcc.CapabilityDenied,
            expected_reason="capability_denied",
            parameters={"id": "123", "value": "x"},
        )
    )

    approval_capsule = compile_for(
        inv,
        update_id,
        policy={"default": "approval"},
    )
    cases.append(
        denied_case(
            "approval_required",
            kcc.Guard.from_capsule(approval_capsule, inventory=inv),
            update_id,
            expected_exception=kcc.ApprovalRequired,
            expected_reason="approval_required",
            parameters={"id": "123", "value": "x"},
        )
    )

    operation_capsule = compile_for(
        inv,
        read_id,
        policy={"default": "allow"},
        constraints={"operations": ["read"]},
    )
    cases.append(
        denied_case(
            "operation_not_granted",
            kcc.Guard.from_capsule(operation_capsule, inventory=inv),
            read_id,
            expected_exception=kcc.AuthorityDenied,
            expected_reason="operation_not_granted",
            operation="delete",
            parameters={"id": "123"},
        )
    )

    parameter_capsule = compile_for(
        inv,
        read_id,
        policy={"default": "allow"},
        constraints={
            "parameters": {
                "id": {"required": True, "type": "string"},
            }
        },
    )
    parameter_guard = kcc.Guard.from_capsule(parameter_capsule, inventory=inv)

    cases.append(
        denied_case(
            "unexpected_parameter_key",
            parameter_guard,
            read_id,
            expected_exception=kcc.AuthorityDenied,
            expected_reason="parameter_not_granted:extra",
            parameters={"id": "123", "extra": "not-compiled"},
        )
    )
    cases.append(
        denied_case(
            "required_parameter_missing",
            parameter_guard,
            read_id,
            expected_exception=kcc.AuthorityDenied,
            expected_reason="required_parameter_missing:id",
            parameters={},
        )
    )
    cases.append(
        denied_case(
            "parameter_type_mismatch",
            parameter_guard,
            read_id,
            expected_exception=kcc.AuthorityDenied,
            expected_reason="parameter_type_mismatch:id",
            parameters={"id": 123},
        )
    )

    expiring_capsule = compile_for(
        inv,
        read_id,
        policy={"default": "allow"},
        ttl_seconds=1,
    )
    cases.append(
        denied_case(
            "expired_capsule",
            kcc.Guard.from_capsule(expiring_capsule, inventory=inv),
            read_id,
            expected_exception=kcc.AuthorityDenied,
            expected_reason="expired",
            parameters={"id": "123"},
            now=101,
            expected_failed_checks={"expiry"},
        )
    )

    drifted_inventory = inventory(drift=True)
    cases.append(
        denied_case(
            "inventory_drift",
            kcc.Guard.from_capsule(read_only_capsule, inventory=drifted_inventory),
            read_id,
            expected_exception=kcc.AuthorityDenied,
            expected_reason="inventory_drift",
            parameters={"id": "123"},
            expected_failed_checks={"inventory", "fingerprints"},
        )
    )

    tampered_capsule = copy.deepcopy(read_only_capsule)
    tampered_capsule["task"] = "tampered after compilation"
    cases.append(
        denied_case(
            "tampered_capsule_integrity",
            kcc.Guard.from_capsule(tampered_capsule, inventory=inv),
            read_id,
            expected_exception=kcc.AuthorityDenied,
            expected_reason="invalid_capsule_integrity",
            parameters={"id": "123"},
            expected_failed_checks={"integrity"},
        )
    )

    evidence = {
        "schema": "kcc.external-diagnostics-dogfood.v1",
        "pass": True,
        "distribution": args.distribution,
        "python": platform.python_version(),
        "package_version": metadata.version("kavi-capability-compiler"),
        "sdk_version": kcc.SDK_VERSION,
        "package_path": str(package_path),
        "cases": cases,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
