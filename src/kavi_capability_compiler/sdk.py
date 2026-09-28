from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from copy import deepcopy
from typing import Any

from .core import authorize_call
from .runtime import ApprovalRequired, AuthorityDenied, CapabilityDenied

SDK_VERSION="kcc.sdk.v1"


class Guard:
    """Portable KCC execution guard.

    The guard is framework-neutral: callers provide a capability id, the exact
    parameters to authorize, and a dispatcher function. Denied calls never
    reach the dispatcher.
    """

    def __init__(
        self,
        capsule: Mapping[str, Any],
        *,
        signed_envelope: Mapping[str, Any] | None = None,
        trusted_keys: Mapping[str, Any] | None = None,
        inventory: Mapping[str, Any] | None = None,
        current_authority_resolver: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    ) -> None:
        self._capsule=deepcopy(dict(capsule))
        self._signed_envelope=deepcopy(dict(signed_envelope)) if signed_envelope is not None else None
        self._trusted_keys=dict(trusted_keys or {})
        self._inventory=deepcopy(dict(inventory)) if inventory is not None else None
        self._current_authority_resolver=current_authority_resolver

    @classmethod
    def from_capsule(
        cls,
        capsule: Mapping[str, Any],
        *,
        inventory: Mapping[str, Any] | None = None,
        current_authority_resolver: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    ) -> "Guard":
        return cls(
            capsule,
            inventory=inventory,
            current_authority_resolver=current_authority_resolver,
        )

    @classmethod
    def from_signed(
        cls,
        envelope: Mapping[str, Any],
        trusted_keys: Mapping[str, Any],
        *,
        now: int | None = None,
        inventory: Mapping[str, Any] | None = None,
        current_authority_resolver: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    ) -> "Guard":
        from .signing import verify_signed_capsule
        result=verify_signed_capsule(envelope,trusted_keys,now=now)
        if not result["valid"]:
            raise AuthorityDenied({"allowed":False,"reason":"signed_capsule_invalid","verification":result})
        return cls(
            envelope["capsule"],
            signed_envelope=envelope,
            trusted_keys=trusted_keys,
            inventory=inventory,
            current_authority_resolver=current_authority_resolver,
        )

    @property
    def capsule_id(self) -> str | None:
        return self._capsule.get("capsule_id")

    @property
    def signed(self) -> bool:
        return self._signed_envelope is not None

    @property
    def inventory_bound(self) -> bool:
        return self._inventory is not None

    @property
    def current_authority_bound(self) -> bool:
        return self._current_authority_resolver is not None

    def _current_authority_context(
        self,
        capability_id: str,
        *,
        operation: str | None,
        parameters: Mapping[str, Any],
        now: int | None,
    ) -> dict[str, Any]:
        return {
            "capsule_id":self.capsule_id,
            "task":self._capsule.get("task"),
            "capability_id":capability_id,
            "operation":operation,
            "parameters":dict(parameters),
            "now":now,
        }

    def _current_authority_decision(
        self,
        state: Any,
        *,
        capsule_decision: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(state,Mapping) or type(state.get("active")) is not bool:
            return {
                "allowed":False,
                "reason":"current_authority_unknown",
                "capsule_decision":dict(capsule_decision),
            }

        current={"active":state["active"]}
        if isinstance(state.get("reason"),str) and state["reason"]:
            current["reason"]=state["reason"]

        if state["active"] is not True:
            return {
                "allowed":False,
                "reason":"current_authority_revoked",
                "current_authority":current,
                "capsule_decision":dict(capsule_decision),
            }

        out=dict(capsule_decision)
        out["current_authority"]=current
        return out

    def _resolve_current_authority(
        self,
        capability_id: str,
        *,
        operation: str | None,
        parameters: Mapping[str, Any],
        now: int | None,
        capsule_decision: Mapping[str, Any],
    ) -> dict[str, Any]:
        resolver=self._current_authority_resolver
        if resolver is None:
            return dict(capsule_decision)

        context=self._current_authority_context(
            capability_id,
            operation=operation,
            parameters=parameters,
            now=now,
        )
        try:
            state=resolver(context)
        except Exception:
            return {
                "allowed":False,
                "reason":"current_authority_resolver_error",
                "capsule_decision":dict(capsule_decision),
            }

        if inspect.isawaitable(state):
            if inspect.iscoroutine(state):
                state.close()
            return {
                "allowed":False,
                "reason":"current_authority_resolver_async_unsupported",
                "capsule_decision":dict(capsule_decision),
            }

        return self._current_authority_decision(
            state,
            capsule_decision=capsule_decision,
        )

    async def _resolve_current_authority_async(
        self,
        capability_id: str,
        *,
        operation: str | None,
        parameters: Mapping[str, Any],
        now: int | None,
        capsule_decision: Mapping[str, Any],
    ) -> dict[str, Any]:
        resolver=self._current_authority_resolver
        if resolver is None:
            return dict(capsule_decision)

        context=self._current_authority_context(
            capability_id,
            operation=operation,
            parameters=parameters,
            now=now,
        )
        try:
            state=resolver(context)
            if inspect.isawaitable(state):
                state=await state
        except Exception:
            return {
                "allowed":False,
                "reason":"current_authority_resolver_error",
                "capsule_decision":dict(capsule_decision),
            }

        return self._current_authority_decision(
            state,
            capsule_decision=capsule_decision,
        )

    def _authorize_capsule(
        self,
        capability_id: str,
        *,
        operation: str | None = None,
        parameters: Mapping[str, Any] | None = None,
        now: int | None = None,
    ) -> dict[str, Any]:
        if self._signed_envelope is not None:
            from .signing import verify_signed_capsule
            verified=verify_signed_capsule(self._signed_envelope,self._trusted_keys,now=now)
            if not verified["valid"]:
                return {
                    "allowed":False,
                    "reason":"signed_capsule_invalid",
                    "verification":verified,
                }
        return authorize_call(
            self._capsule,
            capability_id,
            operation=operation,
            parameters=dict(parameters or {}),
            now=now,
            inventory=self._inventory,
        )

    def authorize(
        self,
        capability_id: str,
        *,
        operation: str | None = None,
        parameters: Mapping[str, Any] | None = None,
        now: int | None = None,
    ) -> dict[str, Any]:
        params=dict(parameters or {})
        decision=self._authorize_capsule(
            capability_id,
            operation=operation,
            parameters=params,
            now=now,
        )
        if not decision["allowed"]:
            return decision
        return self._resolve_current_authority(
            capability_id,
            operation=operation,
            parameters=params,
            now=now,
            capsule_decision=decision,
        )

    def require(
        self,
        capability_id: str,
        *,
        operation: str | None = None,
        parameters: Mapping[str, Any] | None = None,
        now: int | None = None,
    ) -> dict[str, Any]:
        decision=self.authorize(
            capability_id,
            operation=operation,
            parameters=parameters,
            now=now,
        )
        if not decision["allowed"]:
            if decision.get("reason")=="approval_required":
                raise ApprovalRequired(decision)
            if decision.get("reason")=="capability_denied":
                raise CapabilityDenied(decision)
            raise AuthorityDenied(decision)
        return decision

    def dispatch_sync(
        self,
        capability_id: str,
        dispatcher: Callable[[dict[str, Any]], Any],
        *,
        operation: str | None = None,
        parameters: Mapping[str, Any] | None = None,
        now: int | None = None,
    ) -> dict[str, Any]:
        """Authorize then invoke a synchronous host dispatcher."""
        params=dict(parameters or {})
        decision=self.require(
            capability_id,
            operation=operation,
            parameters=params,
            now=now,
        )
        result=dispatcher(params)
        if inspect.isawaitable(result):
            if inspect.iscoroutine(result):
                result.close()
            raise TypeError("dispatcher returned awaitable; use await Guard.dispatch(...)")
        return {
            "executed":True,
            "sdk_version":SDK_VERSION,
            "capsule_id":self.capsule_id,
            "capability_id":capability_id,
            "operation":operation,
            "decision":decision,
            "result":result,
        }

    async def dispatch(
        self,
        capability_id: str,
        dispatcher: Callable[[dict[str, Any]], Any],
        *,
        operation: str | None = None,
        parameters: Mapping[str, Any] | None = None,
        now: int | None = None,
    ) -> dict[str, Any]:
        params=dict(parameters or {})
        decision=self._authorize_capsule(
            capability_id,
            operation=operation,
            parameters=params,
            now=now,
        )
        if decision["allowed"]:
            decision=await self._resolve_current_authority_async(
                capability_id,
                operation=operation,
                parameters=params,
                now=now,
                capsule_decision=decision,
            )
        if not decision["allowed"]:
            if decision.get("reason")=="approval_required":
                raise ApprovalRequired(decision)
            if decision.get("reason")=="capability_denied":
                raise CapabilityDenied(decision)
            raise AuthorityDenied(decision)
        result=dispatcher(params)
        if inspect.isawaitable(result):
            result=await result
        return {
            "executed":True,
            "sdk_version":SDK_VERSION,
            "capsule_id":self.capsule_id,
            "capability_id":capability_id,
            "operation":operation,
            "decision":decision,
            "result":result,
        }
