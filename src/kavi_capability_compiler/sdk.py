from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from copy import deepcopy
from typing import Any

from .core import authorize_call
from .runtime import AuthorityDenied

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
    ) -> None:
        self._capsule=deepcopy(dict(capsule))
        self._signed_envelope=deepcopy(dict(signed_envelope)) if signed_envelope is not None else None
        self._trusted_keys=dict(trusted_keys or {})

    @classmethod
    def from_capsule(cls,capsule: Mapping[str, Any]) -> "Guard":
        return cls(capsule)

    @classmethod
    def from_signed(
        cls,
        envelope: Mapping[str, Any],
        trusted_keys: Mapping[str, Any],
        *,
        now: int | None = None,
    ) -> "Guard":
        from .signing import verify_signed_capsule
        result=verify_signed_capsule(envelope,trusted_keys,now=now)
        if not result["valid"]:
            raise AuthorityDenied({"allowed":False,"reason":"signed_capsule_invalid","verification":result})
        return cls(
            envelope["capsule"],
            signed_envelope=envelope,
            trusted_keys=trusted_keys,
        )

    @property
    def capsule_id(self) -> str | None:
        return self._capsule.get("capsule_id")

    @property
    def signed(self) -> bool:
        return self._signed_envelope is not None

    def authorize(
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
        decision=self.require(
            capability_id,
            operation=operation,
            parameters=params,
            now=now,
        )
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
