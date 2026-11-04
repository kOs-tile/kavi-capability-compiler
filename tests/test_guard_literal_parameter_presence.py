"""Regression: omission must not bypass a literal least-authority constraint."""
from __future__ import annotations

import pytest

import kavi_capability_compiler as kcc


def scoped_guard(rule):
    tools = {"tools": [{
        "name": "read_record",
        "description": "Read one synthetic record",
        "input_schema": {
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
        },
    }]}
    inventory = kcc.scan_manifest(
        kcc.adapt_capabilities(
            "generic", tools, namespace="literal-parameter-regression"
        )
    )
    cid = inventory["capabilities"][0]["id"]
    cap = kcc.compile_capsule(
        inventory, {
            "task": "Read tenant-a-001 only",
            "capabilities": [cid],
            "ttl_seconds": 300,
            "capability_constraints": {
                cid: {
                    "operations": ["read"],
                    "parameters": {"customer_id": rule},
                }
            },
        }, {"default": "allow"}, now=100,
    )
    assert cap["status"] == "ready"
    return kcc.Guard.from_capsule(cap, inventory=inventory), cid


def test_missing_literal_value_fails_closed_before_host_dispatch():
    guard, cid = scoped_guard("tenant-a-001")
    decision = guard.authorize(cid, operation="read", parameters={}, now=101)
    assert decision["allowed"] is False
    assert decision["reason"] == "required_parameter_missing:customer_id"
    side_effects = []
    with pytest.raises(kcc.AuthorityDenied):
        guard.dispatch_sync(
            cid, lambda args: side_effects.append(dict(args)),
            operation="read", parameters={}, now=101,
        )
    assert side_effects == []


@pytest.mark.parametrize("wrong", [
    {"customer_id": "tenant-b-001"},
    {"customer_id": "tenant-a-001", "all_tenants": True},
    {"customer_id": None},
    {"customer_id": "tenant-a-001 "},
])
def test_mismatched_literal_value_stays_denied(wrong):
    guard, cid = scoped_guard("tenant-a-001")
    count = []
    with pytest.raises(kcc.AuthorityDenied):
        guard.dispatch_sync(
            cid, lambda args: count.append(args),
            operation="read", parameters=wrong, now=101,
        )
    assert count == []


def test_exact_literal_value_still_dispatches_one_read():
    guard, cid = scoped_guard("tenant-a-001")
    effects = []
    result = guard.dispatch_sync(
        cid, lambda args: effects.append(dict(args)) or {"synthetic": True},
        operation="read", parameters={"customer_id": "tenant-a-001"},
        now=101,
    )
    assert result["executed"] is True
    assert effects == [{"customer_id": "tenant-a-001"}]


def test_explicit_optional_structured_constraint_preserves_optional_semantics():
    guard, cid = scoped_guard({"type": "string", "required": False})
    result = guard.authorize(cid, operation="read", parameters={}, now=101)
    # A non-literal optional rule allows omission by explicit design;
    # callers must still validate any required tool schema at their boundary.
    assert result["allowed"] is True


def test_explicit_required_structured_constraint_stays_fail_closed():
    guard, cid = scoped_guard({"type": "string", "required": True})
    result = guard.authorize(cid, operation="read", parameters={}, now=101)
    assert result["allowed"] is False
    assert result["reason"] == "required_parameter_missing:customer_id"
