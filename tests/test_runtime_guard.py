import asyncio
from unittest.mock import AsyncMock

import pytest

from kavi_capability_compiler.core import compile_capsule, scan_mcp_snapshot
from kavi_capability_compiler.runtime import (
    AuthorityDenied,
    guarded_dispatch,
    require_authorized_call,
)


CAPABILITY = "mcp:browser:browser_tabs"


def capsule(now=100, ttl=300):
    inventory = scan_mcp_snapshot({
        "server": {"name": "browser"},
        "tools": [{
            "name": "browser_tabs",
            "description": "List, create, close, or select browser tabs.",
            "inputSchema": {
                "type": "object",
                "properties": {"tab_index": {"type": "integer"}},
            },
        }],
    })
    return compile_capsule(
        inventory,
        {
            "task": "Inspect existing tabs only",
            "capabilities": [CAPABILITY],
            "ttl_seconds": ttl,
            "capability_constraints": {
                CAPABILITY: {
                    "operations": ["list"],
                    "parameters": {
                        "tab_index": {
                            "type": "integer",
                            "min": 0,
                            "max": 3,
                        }
                    },
                }
            },
        },
        {"default": "allow"},
        now=now,
    )


def test_denied_operation_never_reaches_dispatcher():
    dispatch = AsyncMock(return_value={"ok": True})

    async def run():
        with pytest.raises(AuthorityDenied) as exc:
            await guarded_dispatch(
                capsule(),
                CAPABILITY,
                dispatch,
                operation="close",
                parameters={"tab_index": 1},
                now=101,
            )
        return exc.value

    denied = asyncio.run(run())
    assert denied.decision["reason"] == "operation_not_granted"
    dispatch.assert_not_awaited()


def test_allowed_operation_dispatches_exact_authorized_parameters():
    dispatch = AsyncMock(return_value={"tabs": ["one", "two"]})
    params = {"tab_index": 2}

    result = asyncio.run(
        guarded_dispatch(
            capsule(),
            CAPABILITY,
            dispatch,
            operation="list",
            parameters=params,
            now=101,
        )
    )

    assert result["executed"] is True
    assert result["decision"]["allowed"] is True
    assert result["result"] == {"tabs": ["one", "two"]}
    dispatch.assert_awaited_once_with(params)


def test_expired_capsule_raises_before_execution():
    with pytest.raises(AuthorityDenied) as exc:
        require_authorized_call(
            capsule(now=100, ttl=1),
            CAPABILITY,
            operation="list",
            parameters={"tab_index": 1},
            now=101,
        )

    assert exc.value.decision["reason"] == "expired"


def test_parameter_escape_raises_before_execution():
    with pytest.raises(AuthorityDenied) as exc:
        require_authorized_call(
            capsule(),
            CAPABILITY,
            operation="list",
            parameters={"tab_index": 99},
            now=101,
        )

    assert exc.value.decision["reason"] == "parameter_above_max:tab_index"


def test_sync_dispatcher_is_supported():
    calls = []

    def dispatch(params):
        calls.append(params)
        return {"ok": True}

    result = asyncio.run(
        guarded_dispatch(
            capsule(),
            CAPABILITY,
            dispatch,
            operation="list",
            parameters={"tab_index": 0},
            now=101,
        )
    )

    assert result["result"] == {"ok": True}
    assert calls == [{"tab_index": 0}]


def test_dispatcher_exception_propagates_after_authorization():
    def dispatch(_params):
        raise RuntimeError("tool failed")

    async def run():
        await guarded_dispatch(
            capsule(),
            CAPABILITY,
            dispatch,
            operation="list",
            parameters={"tab_index": 0},
            now=101,
        )

    with pytest.raises(RuntimeError, match="tool failed"):
        asyncio.run(run())
