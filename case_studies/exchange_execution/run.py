from __future__ import annotations

import json

import kavi_capability_compiler as kcc


def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


def main() -> None:
    manifest = kcc.adapt_capabilities(
        "generic",
        {
            "tools": [
                _tool(
                    "create_limit_order",
                    "Create a live limit order on an exchange trading venue.",
                    {
                        "symbol": {"type": "string"},
                        "side": {"type": "string"},
                        "quantity": {"type": "number"},
                        "limit_price": {"type": "number"},
                    },
                    ["symbol", "side", "quantity", "limit_price"],
                ),
                _tool(
                    "create_market_order",
                    "Create a live market order on an exchange trading venue.",
                    {
                        "symbol": {"type": "string"},
                        "side": {"type": "string"},
                        "quantity": {"type": "number"},
                    },
                    ["symbol", "side", "quantity"],
                ),
                _tool(
                    "fetch_order",
                    "Fetch order status from an exchange trading venue.",
                    {
                        "order_id": {"type": "string"},
                        "symbol": {"type": "string"},
                    },
                    ["order_id", "symbol"],
                ),
            ]
        },
        namespace="real-consumer-exchange",
    )
    inventory = kcc.scan_manifest(manifest)
    by_name = {cap["name"]: cap for cap in inventory["capabilities"]}

    assert by_name["create_limit_order"]["effect"] == "financial"
    assert by_name["create_market_order"]["effect"] == "financial"
    assert by_name["fetch_order"]["effect"] == "read"

    limit_id = by_name["create_limit_order"]["id"]
    market_id = by_name["create_market_order"]["id"]

    approved = {
        "symbol": "BTC/USDT",
        "side": "buy",
        "quantity": 0.02,
        "limit_price": 50_000.0,
    }

    intent = {
        "task": "submit exactly one approved exchange limit-order leg",
        "capabilities": [limit_id],
        "ttl_seconds": 120,
        "capability_constraints": {
            limit_id: {
                "operations": ["submit"],
                "parameters": {
                    "symbol": {
                        "required": True,
                        "type": "string",
                        "enum": [approved["symbol"]],
                    },
                    "side": {
                        "required": True,
                        "type": "string",
                        "enum": [approved["side"]],
                    },
                    "quantity": {
                        "required": True,
                        "type": "number",
                        "min": approved["quantity"],
                        "max": approved["quantity"],
                    },
                    "limit_price": {
                        "required": True,
                        "type": "number",
                        "min": approved["limit_price"],
                        "max": approved["limit_price"],
                    },
                },
            }
        },
    }
    policy = {
        "default": "deny",
        "allow": [{"capabilities": [limit_id]}],
    }
    capsule = kcc.compile_capsule(inventory, intent, policy, now=100)
    assert capsule["status"] == "ready"

    host_calls: list[dict] = []

    def exchange_dispatch(params: dict) -> dict:
        # Consumer-owned metadata is injected only after KCC authorization. The
        # agent never receives authority over the exchange idempotency field.
        call = {
            **params,
            "host_params": {"newClientOrderId": "host-derived-idempotency-key"},
        }
        host_calls.append(call)
        return {"id": "exchange-order-1", "status": "open"}

    guard = kcc.Guard.from_capsule(capsule, inventory=inventory)
    allowed = guard.dispatch_sync(
        limit_id,
        exchange_dispatch,
        operation="submit",
        parameters=approved,
        now=101,
    )
    assert allowed["executed"] is True
    assert allowed["result"]["id"] == "exchange-order-1"
    assert len(host_calls) == 1
    assert host_calls[0]["host_params"]["newClientOrderId"] == "host-derived-idempotency-key"

    denied_reasons: dict[str, str] = {}

    def expect_denied(label: str, capability_id: str, params: dict, expected: str) -> None:
        before = len(host_calls)
        try:
            guard.dispatch_sync(
                capability_id,
                exchange_dispatch,
                operation="submit",
                parameters=params,
                now=101,
            )
        except kcc.AuthorityDenied as exc:
            assert exc.reason == expected, (label, exc.decision)
            denied_reasons[label] = exc.reason
        else:
            raise AssertionError(f"{label} must be denied before host dispatch")
        assert len(host_calls) == before, label

    expect_denied(
        "wrong_symbol",
        limit_id,
        {**approved, "symbol": "ETH/USDT"},
        "parameter_not_allowed:symbol",
    )
    expect_denied(
        "opposite_side",
        limit_id,
        {**approved, "side": "sell"},
        "parameter_not_allowed:side",
    )
    expect_denied(
        "larger_quantity",
        limit_id,
        {**approved, "quantity": 0.03},
        "parameter_above_max:quantity",
    )
    expect_denied(
        "market_order_outside_capsule",
        market_id,
        {
            "symbol": approved["symbol"],
            "side": approved["side"],
            "quantity": approved["quantity"],
        },
        "capability_not_granted",
    )

    evidence = {
        "validation": "kcc.real-consumer.exchange-execution.v1",
        "pass": True,
        "inventory_capabilities": len(inventory["capabilities"]),
        "limit_order_effect": by_name["create_limit_order"]["effect"],
        "market_order_effect": by_name["create_market_order"]["effect"],
        "fetch_order_effect": by_name["fetch_order"]["effect"],
        "compiled_grants": len(capsule["grants"]),
        "allowed_host_dispatches": len(host_calls),
        "denied_host_dispatches": 0,
        "denied_reasons": denied_reasons,
        "host_injected_idempotency": True,
        "network_or_exchange_call_performed": False,
        "model_or_api_call_performed": False,
    }
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
