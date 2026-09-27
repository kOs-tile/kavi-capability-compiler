"""Portable runtime guard helpers.

KCC remains transport/framework agnostic. These helpers place authorize_call()
immediately in front of an application-supplied dispatcher and guarantee that a
denied decision never reaches that dispatcher.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from .core import authorize_call


class AuthorityDenied(RuntimeError):
    """Raised when a KCC capsule does not authorize a requested dispatch."""

    def __init__(self, decision: dict[str, Any]) -> None:
        self.decision = decision
        self.reason = str(decision.get("reason", "authority_denied"))
        super().__init__(self.reason)


class ApprovalRequired(AuthorityDenied):
    """Raised when authority exists only behind an external approval handoff."""


class CapabilityDenied(AuthorityDenied):
    """Raised when policy explicitly denies the requested capability."""


def require_authorized_call(
    capsule: dict[str, Any],
    capability_id: str,
    operation: str | None = None,
    parameters: dict[str, Any] | None = None,
    *,
    now: int | None = None,
) -> dict[str, Any]:
    """Return the authorization decision or raise before dispatch."""
    decision = authorize_call(
        capsule,
        capability_id,
        operation=operation,
        parameters=parameters or {},
        now=now,
    )
    if not decision["allowed"]:
        if decision.get("reason")=="approval_required":
            raise ApprovalRequired(decision)
        if decision.get("reason")=="capability_denied":
            raise CapabilityDenied(decision)
        raise AuthorityDenied(decision)
    return decision


async def guarded_dispatch(
    capsule: dict[str, Any],
    capability_id: str,
    dispatcher: Callable[[dict[str, Any]], Any],
    *,
    operation: str | None = None,
    parameters: dict[str, Any] | None = None,
    now: int | None = None,
) -> dict[str, Any]:
    """Authorize first, then invoke exactly one caller-supplied dispatcher.

    The dispatcher receives the same parameter mapping that was authorized.
    Sync and async dispatchers are supported. Dispatcher exceptions propagate;
    KCC does not reinterpret execution failure as an authorization decision.
    """
    params = dict(parameters or {})
    decision = require_authorized_call(
        capsule,
        capability_id,
        operation=operation,
        parameters=params,
        now=now,
    )

    result = dispatcher(params)
    if inspect.isawaitable(result):
        result = await result

    return {
        "executed": True,
        "capsule_id": capsule.get("capsule_id"),
        "capability_id": capability_id,
        "operation": operation,
        "decision": decision,
        "result": result,
    }
