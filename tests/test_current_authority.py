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
