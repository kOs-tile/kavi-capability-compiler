"""Five-minute, credential-free KCC authority-boundary demonstration.

Run after installing the published KCC v0.1.1 wheel:
    python examples/recruiter_demo.py

This demo uses synthetic data only. KCC authorizes a caller-owned dispatcher;
no actual CRM, model, network, or filesystem mutations are performed.
"""

from __future__ import annotations

import json
from typing import Any

import kavi_capability_compiler as kcc


FIXED_NOW = 100
CUSTOMER_ID = "demo-customer-001"


def run_demo() -> dict[str, Any]:
    tools = {
        "tools": [
            {
                "name": "read_customer",
                "description": "Read a customer record by ID",
                "input_schema": {
                    "type": "object",
                    "properties": {"customer_id": {"type": "string"}},
                    "required": ["customer_id"],
                },
            },
            {
                "name": "delete_customer",
                "description": "Delete a customer record by ID",
                "input_schema": {
                    "type": "object",
                    "properties": {"customer_id": {"type": "string"}},
                    "required": ["customer_id"],
                },
            },
        ]
    }
    manifest = kcc.adapt_capabilities("generic", tools, namespace="recruiter-demo")
    inventory = kcc.scan_manifest(manifest)
    ids = {cap["name"]: cap["id"] for cap in inventory["capabilities"]}
    read_id, delete_id = ids["read_customer"], ids["delete_customer"]

    capsule = kcc.compile_capsule(
        inventory,
        {
            "task": "Read exactly one synthetic customer; never delete anyone",
            "capabilities": [read_id],
            "ttl_seconds": 300,
            "capability_constraints": {
                read_id: {"parameters": {"customer_id": CUSTOMER_ID}}
            },
        },
        {"default": "allow"},
        now=FIXED_NOW,
    )
    assert capsule["status"] == "ready"
    guard = kcc.Guard.from_capsule(capsule, inventory=inventory)
    assert guard.inventory_bound

    dispatcher_calls: dict[str, list[dict[str, Any]]] = {"read": [], "delete": []}

    def read_dispatcher(params: dict[str, Any]) -> dict[str, str]:
        dispatcher_calls["read"].append(dict(params))
        return {"customer_id": params["customer_id"], "status": "demo-only"}

    def delete_dispatcher(params: dict[str, Any]) -> dict[str, bool]:
        dispatcher_calls["delete"].append(dict(params))
        return {"deleted": True}

    def blocked(
        label: str,
        guarded: kcc.Guard,
        capability_id: str,
        dispatcher: Any,
        parameters: dict[str, Any],
        expected_exception: type[kcc.AuthorityDenied],
        expected_reason: str,
        *,
        now: int = FIXED_NOW + 1,
    ) -> str:
        before = (len(dispatcher_calls["read"]), len(dispatcher_calls["delete"]))
        try:
            guarded.dispatch_sync(capability_id, dispatcher, parameters=parameters, now=now)
        except expected_exception as exc:
            assert exc.reason == expected_reason, (label, exc.decision)
        else:
            raise AssertionError(f"{label}: authorization unexpectedly reached dispatcher")
        after = (len(dispatcher_calls["read"]), len(dispatcher_calls["delete"]))
        assert after == before, f"{label}: denied call reached host dispatcher"
        print(f"  BLOCK {label}: {expected_reason} [dispatcher unchanged]")
        return expected_reason

    print(f"KCC {kcc.__version__} | 5-minute hiring demo | no external calls")
    print(f"Inventory: {len(inventory['capabilities'])} capabilities; task grant: 1 read")

    granted = guard.dispatch_sync(
        read_id, read_dispatcher, parameters={"customer_id": CUSTOMER_ID}, now=101
    )
    assert granted["executed"] is True
    assert granted["result"] == {"customer_id": CUSTOMER_ID, "status": "demo-only"}
    assert dispatcher_calls["read"] == [{"customer_id": CUSTOMER_ID}]
    print("  ALLOW read_customer(demo-customer-001): dispatched exactly once")

    reasons = {
        "ungranted_deletion": blocked(
            "ungranted deletion", guard, delete_id, delete_dispatcher,
            {"customer_id": CUSTOMER_ID}, kcc.AuthorityDenied, "capability_not_granted"
        ),
        "wrong_customer": blocked(
            "wrong customer", guard, read_id, read_dispatcher,
            {"customer_id": "someone-else"}, kcc.AuthorityDenied,
            "parameter_mismatch:customer_id"
        ),
        "extra_argument": blocked(
            "extra argument", guard, read_id, read_dispatcher,
            {"customer_id": CUSTOMER_ID, "export": True},
            kcc.AuthorityDenied, "parameter_not_granted:export"
        ),
        "expired_capsule": blocked(
            "expired capsule", guard, read_id, read_dispatcher,
            {"customer_id": CUSTOMER_ID}, kcc.AuthorityDenied, "expired", now=401
        ),
    }

    approval_capsule = kcc.compile_capsule(
        inventory,
        {"task": "Request deletion; requires external human approval", "capabilities": [delete_id]},
        {"default": "deny", "approval": [{"capabilities": [delete_id]}]},
        now=FIXED_NOW,
    )
    assert approval_capsule["status"] == "approval_required"
    approval_guard = kcc.Guard.from_capsule(approval_capsule, inventory=inventory)
    reasons["approval_required"] = blocked(
        "human-approval gate", approval_guard, delete_id, delete_dispatcher,
        {"customer_id": CUSTOMER_ID}, kcc.ApprovalRequired, "approval_required"
    )

    assert dispatcher_calls == {"read": [{"customer_id": CUSTOMER_ID}], "delete": []}
    report = {
        "status": "PASS",
        "kcc_version": kcc.__version__,
        "cases": 6,
        "allowed_dispatches": len(dispatcher_calls["read"]),
        "denied_dispatches": 0,
        "delete_dispatches": len(dispatcher_calls["delete"]),
        "denial_reasons": reasons,
        "synthetic_data_only": True,
    }
    print("KCC_5_MIN_DEMO: PASS")
    print("EVIDENCE_JSON=" + json.dumps(report, sort_keys=True))
    return report


if __name__ == "__main__":
    run_demo()
