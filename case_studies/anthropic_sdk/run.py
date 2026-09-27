from __future__ import annotations

import json

import anthropic
from anthropic import beta_tool

import kavi_capability_compiler as kcc


get_invocations=[]
update_invocations=[]
delete_invocations=[]


@beta_tool
def get_record(id: str) -> str:
    """Get one record by ID.

    Args:
        id: Record identifier.
    """
    get_invocations.append(id)
    return f"record:{id}"


@beta_tool
def update_record(id: str, value: str) -> str:
    """Update one record.

    Args:
        id: Record identifier.
        value: Replacement value.
    """
    update_invocations.append((id,value))
    return f"updated:{id}"


@beta_tool
def delete_record(id: str) -> str:
    """Delete one record.

    Args:
        id: Record identifier.
    """
    delete_invocations.append(id)
    return f"deleted:{id}"


def inventory_for(tools):
    definitions=[]
    for tool in tools:
        serialized=tool.to_dict()
        assert serialized["name"]==tool.name
        assert isinstance(serialized["input_schema"],dict)
        assert callable(tool.call)
        definitions.append(serialized)
    manifest=kcc.adapt_capabilities(
        "anthropic",
        {"tools":definitions},
        namespace="anthropic-sdk",
    )
    return manifest,kcc.scan_manifest(manifest)


def main():
    tools=[get_record,update_record]
    manifest,inventory=inventory_for(tools)
    ids={item["name"]:item["id"] for item in inventory["capabilities"]}

    capsule=kcc.compile_capsule(
        inventory,
        {
            "task":"Read one record without mutation",
            "capabilities":[ids["get_record"]],
            "capability_constraints":{
                ids["get_record"]:{
                    "parameters":{
                        "id":{"required":True,"type":"string"},
                    }
                }
            },
            "ttl_seconds":60,
        },
        {"default":"allow"},
        now=100,
    )
    guard=kcc.Guard.from_capsule(capsule,inventory=inventory)

    allowed=guard.dispatch_sync(
        ids["get_record"],
        lambda params: get_record.call(params),
        parameters={"id":"REC-1"},
        now=101,
    )
    assert allowed["executed"] is True
    assert get_invocations==["REC-1"]

    before=len(update_invocations)
    denied_reason=None
    try:
        guard.dispatch_sync(
            ids["update_record"],
            lambda params: update_record.call(params),
            parameters={"id":"REC-1","value":"blocked"},
            now=101,
        )
        raise AssertionError("outside-capsule Anthropic beta tool executed")
    except kcc.AuthorityDenied as exc:
        denied_reason=exc.reason
    assert denied_reason=="capability_not_granted"
    assert len(update_invocations)==before

    _,expanded_inventory=inventory_for([get_record,update_record,delete_record])
    drift=kcc.Guard.from_capsule(
        capsule,
        inventory=expanded_inventory,
    ).authorize(
        ids["get_record"],
        parameters={"id":"REC-1"},
        now=101,
    )
    assert drift["allowed"] is False
    assert drift["reason"]=="inventory_drift"
    assert delete_invocations==[]

    result={
        "validation":"kcc.anthropic-sdk.v1",
        "anthropic_version":anthropic.__version__,
        "beta_tool_count":len(tools),
        "manifest_version":manifest["schema_version"],
        "inventory_version":inventory["version"],
        "capsule_version":capsule["version"],
        "guard_inventory_bound":guard.inventory_bound,
        "allowed_sdk_invocations":len(get_invocations),
        "denied_sdk_invocations":len(update_invocations),
        "denied_reason":denied_reason,
        "expanded_surface_reason":drift["reason"],
        "model_or_api_call_performed":False,
        "pass":True,
    }
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
