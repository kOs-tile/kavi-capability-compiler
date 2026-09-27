from __future__ import annotations

from typing import Any

import kavi_capability_compiler as kcc


def exercise_kit(
    source_format: str,
    payload: Any,
    *,
    namespace: str,
    server: str | None = None,
) -> dict[str, str]:
    """Run one vendor-neutral integration shape through the same KCC boundary."""
    manifest=kcc.adapt_capabilities(
        source_format,
        payload,
        namespace=namespace,
        server=server,
    )
    inventory=kcc.scan_manifest(manifest)
    ids={c["name"]:c["id"] for c in inventory["capabilities"]}
    read_id=ids["get_record"]
    update_id=ids["update_record"]

    capsule=kcc.compile_capsule(
        inventory,
        {
            "task":"Read one record without mutation",
            "capabilities":[read_id],
            "capability_constraints":{
                read_id:{
                    "parameters":{
                        "id":"123",
                    }
                }
            },
        },
        {"default":"allow"},
        now=100,
    )
    guard=kcc.Guard.from_capsule(capsule,inventory=inventory)
    assert guard.inventory_bound

    read_calls=[]
    def read_dispatcher(params):
        read_calls.append(dict(params))
        return {"id":params["id"],"value":"example"}

    result=guard.dispatch_sync(
        read_id,
        read_dispatcher,
        parameters={"id":"123"},
        now=101,
    )
    assert result["executed"] is True
    assert result["result"]=={"id":"123","value":"example"}
    assert read_calls==[{"id":"123"}]

    mutation_calls=[]
    def mutation_dispatcher(params):
        mutation_calls.append(dict(params))
        return {"updated":True}

    try:
        guard.dispatch_sync(
            update_id,
            mutation_dispatcher,
            parameters={"id":"123","value":"blocked"},
            now=101,
        )
        raise AssertionError("outside-capsule mutation reached dispatcher")
    except kcc.AuthorityDenied as exc:
        denied_reason=exc.reason

    assert denied_reason=="capability_not_granted"
    assert mutation_calls==[]

    return {
        "format":source_format,
        "manifest_version":manifest["schema_version"],
        "inventory_version":inventory["version"],
        "capsule_version":capsule["version"],
        "grant":read_id,
    }
