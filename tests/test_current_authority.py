import pytest

import kavi_capability_compiler as kcc


def _context():
    manifest = kcc.adapt_capabilities(
        "generic",
        {
            "tools": [
                {
                    "name": "update_record",
                    "description": "Update one bounded record",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "value": {"type": "string"},
                        },
                        "required": ["id", "value"],
                    },
                },
                {
                    "name": "delete_record",
                    "description": "Delete one record",
                    "input_schema": {
                        "type": "object",
                        "properties": {"id": {"type": "string"}},
                        "required": ["id"],
                    },
                }
            ]
        },
        namespace="records",
    )
    inventory = kcc.scan_manifest(manifest)
    capability_id = inventory["capabilities"][0]["id"]
    capsule = kcc.compile_capsule(
        inventory,
        {
            "task": "update assigned record",
            "capabilities": [capability_id],
            "ttl_seconds": 300,
            "capability_constraints": {
                capability_id: {
                    "operations": ["update"],
                    "parameters": {
                        "id": {"type": "string", "enum": ["record-1"]},
                        "value": {"type": "string", "max_length": 32},
                    },
                }
            },
        },
        {"default": "allow"},
        now=100,
    )
    return inventory, capability_id, capsule


def test_guard_denies_stale_capsule_after_host_revokes_current_authority():
    """
    A capsule can remain cryptographically valid and unexpired after the host
    reassigns/revokes the underlying authority. Guard must be able to consult a
    host-owned current-authority resolver immediately before dispatch so the
    stale worker cannot execute the side effect.
    """
    inventory, capability_id, capsule = _context()
    authority_state = {
        "active": True,
        "reason": "active",
    }
    resolver_calls = []

    def current_authority_resolver(context):
        resolver_calls.append(dict(context))
        return dict(authority_state)

    guard = kcc.Guard.from_capsule(
        capsule,
        inventory=inventory,
        current_authority_resolver=current_authority_resolver,
    )

    dispatches = []

    def dispatcher(parameters):
        dispatches.append(dict(parameters))
        return {"ok": True}

    first = guard.dispatch_sync(
        capability_id,
        dispatcher,
        operation="update",
        parameters={"id": "record-1", "value": "first"},
        now=101,
    )
    assert first["executed"] is True
    assert dispatches == [{"id": "record-1", "value": "first"}]

    # External authoritative state changes without mutating the still-valid
    # capsule: approval withdrawn, grant revoked, or task reassigned.
    authority_state.update(
        active=False,
        reason="authority_revoked",
    )

    with pytest.raises(kcc.AuthorityDenied) as exc:
        guard.dispatch_sync(
            capability_id,
            dispatcher,
            operation="update",
            parameters={"id": "record-1", "value": "second"},
            now=102,
        )

    assert exc.value.reason == "current_authority_revoked"
    assert dispatches == [{"id": "record-1", "value": "first"}]

    # The resolver is a dispatch-time attenuation gate, not a source of new
    # authority. It must be consulted for both attempts against the same capsule.
    assert len(resolver_calls) == 2
    assert all(call["capsule_id"] == capsule["capsule_id"] for call in resolver_calls)
    assert all(call["capability_id"] == capability_id for call in resolver_calls)



def test_current_authority_unknown_fails_closed_before_dispatch():
    inventory, capability_id, capsule = _context()
    guard = kcc.Guard.from_capsule(
        capsule,
        inventory=inventory,
        current_authority_resolver=lambda context: {"reason": "state_unavailable"},
    )
    dispatches = []

    with pytest.raises(kcc.AuthorityDenied) as exc:
        guard.dispatch_sync(
            capability_id,
            lambda parameters: dispatches.append(dict(parameters)),
            operation="update",
            parameters={"id": "record-1", "value": "x"},
            now=101,
        )

    assert exc.value.reason == "current_authority_unknown"
    assert dispatches == []


def test_current_authority_resolver_error_fails_closed_before_dispatch():
    inventory, capability_id, capsule = _context()

    def resolver(_context):
        raise RuntimeError("control plane unavailable")

    guard = kcc.Guard.from_capsule(
        capsule,
        inventory=inventory,
        current_authority_resolver=resolver,
    )
    dispatches = []

    with pytest.raises(kcc.AuthorityDenied) as exc:
        guard.dispatch_sync(
            capability_id,
            lambda parameters: dispatches.append(dict(parameters)),
            operation="update",
            parameters={"id": "record-1", "value": "x"},
            now=101,
        )

    assert exc.value.reason == "current_authority_resolver_error"
    assert dispatches == []


def test_current_authority_resolver_cannot_widen_capsule_authority():
    inventory, capability_id, capsule = _context()
    resolver_calls = []

    def resolver(context):
        resolver_calls.append(dict(context))
        return {"active": True, "reason": "active"}

    guard = kcc.Guard.from_capsule(
        capsule,
        inventory=inventory,
        current_authority_resolver=resolver,
    )
    dispatches = []

    ungranted_capability = next(
        item["id"]
        for item in inventory["capabilities"]
        if item["name"] == "delete_record"
    )

    with pytest.raises(kcc.AuthorityDenied) as exc:
        guard.dispatch_sync(
            ungranted_capability,
            lambda parameters: dispatches.append(dict(parameters)),
            operation="delete",
            parameters={"id": "record-1"},
            now=101,
        )

    assert exc.value.reason == "capability_not_granted"
    assert resolver_calls == []
    assert dispatches == []


def test_current_authority_async_resolver_fails_closed_in_sync_guard():
    inventory, capability_id, capsule = _context()

    async def resolver(_context):
        return {"active": True}

    guard = kcc.Guard.from_capsule(
        capsule,
        inventory=inventory,
        current_authority_resolver=resolver,
    )
    dispatches = []

    with pytest.raises(kcc.AuthorityDenied) as exc:
        guard.dispatch_sync(
            capability_id,
            lambda parameters: dispatches.append(dict(parameters)),
            operation="update",
            parameters={"id": "record-1", "value": "x"},
            now=101,
        )

    assert exc.value.reason == "current_authority_resolver_async_unsupported"
    assert dispatches == []



def test_async_dispatch_supports_async_current_authority_resolver():
    import asyncio

    inventory, capability_id, capsule = _context()
    authority_state = {"active": True, "reason": "active"}
    resolver_calls = []

    async def resolver(context):
        resolver_calls.append(dict(context))
        return dict(authority_state)

    guard = kcc.Guard.from_capsule(
        capsule,
        inventory=inventory,
        current_authority_resolver=resolver,
    )
    dispatches = []

    async def dispatcher(parameters):
        dispatches.append(dict(parameters))
        return {"ok": True}

    first = asyncio.run(
        guard.dispatch(
            capability_id,
            dispatcher,
            operation="update",
            parameters={"id": "record-1", "value": "first"},
            now=101,
        )
    )
    assert first["executed"] is True
    assert dispatches == [{"id": "record-1", "value": "first"}]

    authority_state.update(active=False, reason="task_reassigned")

    with pytest.raises(kcc.AuthorityDenied) as exc:
        asyncio.run(
            guard.dispatch(
                capability_id,
                dispatcher,
                operation="update",
                parameters={"id": "record-1", "value": "second"},
                now=102,
            )
        )

    assert exc.value.reason == "current_authority_revoked"
    assert dispatches == [{"id": "record-1", "value": "first"}]
    assert len(resolver_calls) == 2
