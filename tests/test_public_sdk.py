import asyncio

import kavi_capability_compiler as kcc


def _inventory():
    manifest=kcc.adapt_capabilities(
        "generic",
        {"tools":[
            {"name":"get_record","description":"Get record","input_schema":{"type":"object","properties":{"id":{"type":"string"}},"required":["id"]}},
            {"name":"update_record","description":"Update record","input_schema":{"type":"object","properties":{"id":{"type":"string"},"value":{"type":"string"}},"required":["id","value"]}},
        ]},
        namespace="records",
    )
    return kcc.scan_manifest(manifest)


def test_public_api_exposes_framework_neutral_sdk():
    assert kcc.SDK_VERSION=="kcc.sdk.v1"
    assert kcc.SCHEMA_VERSION=="kcc.capabilities.v1"
    assert kcc.INVENTORY_VERSION=="kcc.inventory.v1"
    assert kcc.INVENTORY_LOCK_VERSION=="kcc.inventory-lock.v1"
    assert kcc.CAPSULE_VERSION=="kcc.capsule.v1"
    assert kcc.DELEGATION_REQUEST_VERSION=="kcc.delegation-request.v1"
    assert kcc.DELEGATED_CAPSULE_VERSION=="kcc.delegated-capsule.v1"
    assert "openai" in kcc.SUPPORTED_SOURCE_FORMATS
    assert callable(kcc.Guard)


def test_embedded_guard_dispatches_inside_host_application_only():
    inv=_inventory()
    ids={x["name"]:x["id"] for x in inv["capabilities"]}
    cap=kcc.compile_capsule(
        inv,
        {"task":"read","capabilities":[ids["get_record"]]},
        {"default":"allow"},
        now=100,
    )
    guard=kcc.Guard.from_capsule(cap)
    calls=[]
    async def dispatch(params):
        calls.append(dict(params))
        return {"record":"ok"}

    out=asyncio.run(guard.dispatch(ids["get_record"],dispatch,parameters={"id":"1"},now=101))
    assert out["result"]=={"record":"ok"}
    assert calls==[{"id":"1"}]

    before=len(calls)
    try:
        asyncio.run(guard.dispatch(ids["update_record"],dispatch,parameters={"id":"1","value":"x"},now=101))
        assert False, "expected AuthorityDenied"
    except kcc.AuthorityDenied as exc:
        assert exc.decision["reason"]=="capability_not_granted"
    assert len(calls)==before


def test_host_can_distinguish_approval_handoff_from_denial():
    inv=_inventory()
    ids={x["name"]:x["id"] for x in inv["capabilities"]}
    cap=kcc.compile_capsule(
        inv,
        {"task":"update","capabilities":[ids["update_record"]]},
        {"default":"approval"},
        now=100,
    )
    guard=kcc.Guard.from_capsule(cap)
    decision=guard.authorize(ids["update_record"],parameters={"id":"1","value":"x"},now=101)
    assert decision["reason"]=="approval_required"
    try:
        guard.require(ids["update_record"],parameters={"id":"1","value":"x"},now=101)
        assert False, "expected ApprovalRequired"
    except kcc.ApprovalRequired as exc:
        assert exc.decision["reason"]=="approval_required"


def test_sync_dispatch_works_without_event_loop():
    inv=_inventory()
    ids={x["name"]:x["id"] for x in inv["capabilities"]}
    cap=kcc.compile_capsule(inv,{"capabilities":[ids["get_record"]]},{"default":"allow"},now=100)
    guard=kcc.Guard.from_capsule(cap)
    calls=[]
    def dispatch(params):
        calls.append(dict(params))
        return {"ok":True}
    out=guard.dispatch_sync(ids["get_record"],dispatch,parameters={"id":"1"},now=101)
    assert out["executed"] is True
    assert out["result"]=={"ok":True}
    assert calls==[{"id":"1"}]


def test_public_api_contract_is_explicit_and_framework_neutral():
    expected={
        "__version__","SDK_VERSION","SCHEMA_VERSION","INVENTORY_VERSION",
        "INVENTORY_LOCK_VERSION","CAPSULE_VERSION","DELEGATION_REQUEST_VERSION",
        "DELEGATED_CAPSULE_VERSION","SUPPORTED_SOURCE_FORMATS",
        "adapt_capabilities","build_manifest","scan_manifest","compile_capsule",
        "verify_capsule","attenuate_capsule","verify_delegated_capsule",
        "authorize_call","capability_id","inventory_lock","diff_inventory_lock",
        "Guard","AuthorityDenied","ApprovalRequired","CapabilityDenied",
        "get_schema","schema_names",
    }
    assert set(kcc.__all__)==expected
    assert not any("kavi" in name.lower() or "hermes" in name.lower() or "codex" in name.lower() for name in kcc.__all__)


def test_packaged_public_schemas_are_available():
    names=kcc.schema_names()
    assert names==(
        "kcc.capabilities.v1",
        "kcc.capsule.v1",
        "kcc.delegated-capsule.v1",
        "kcc.delegation-request.v1",
        "kcc.inventory-lock.v1",
        "kcc.inventory.v1",
        "kcc.signed-capsule.v1",
    )
    capabilities=kcc.get_schema("kcc.capabilities.v1")
    inventory=kcc.get_schema("kcc.inventory.v1")
    inventory_lock=kcc.get_schema("kcc.inventory-lock.v1")
    capsule=kcc.get_schema("kcc.capsule.v1")
    delegation_request=kcc.get_schema("kcc.delegation-request.v1")
    delegated=kcc.get_schema("kcc.delegated-capsule.v1")
    signed=kcc.get_schema("kcc.signed-capsule.v1")
    assert capabilities["title"]=="KCC Universal Capability Manifest"
    assert inventory["title"]=="KCC Capability Inventory"
    assert inventory_lock["title"]=="KCC Inventory Lock"
    assert capsule["title"]=="KCC Execution Capsule"
    assert delegation_request["title"]=="KCC Delegation Request"
    assert delegated["title"]=="KCC Delegated Capsule Envelope"
    assert delegated["properties"]["child_capsule"]["$ref"]=="kcc.capsule.v1.schema.json"
    assert signed["title"]=="KCC Signed Capsule Envelope"
    assert signed["properties"]["capsule"]["$ref"]=="kcc.capsule.v1.schema.json"


def test_public_capability_id_matches_mcp_and_manifest_inventory_identity():
    from kavi_capability_compiler.core import scan_mcp_snapshot

    mcp_expected=kcc.capability_id("MCP"," Research Desk ","Fetch:Price%Now")
    assert mcp_expected=="mcp:research-desk:fetch%3aprice%25now"
    mcp_inventory=scan_mcp_snapshot({
        "server":{"name":" Research Desk "},
        "tools":[{
            "name":"Fetch:Price%Now",
            "description":"Fetch a bounded price record.",
            "inputSchema":{"type":"object","properties":{}},
        }],
    })
    assert mcp_inventory["capabilities"][0]["id"]==mcp_expected

    manifest=kcc.adapt_capabilities(
        "generic",
        {"tools":[{
            "name":"Fetch:Price%Now",
            "description":"Fetch a bounded price record.",
            "input_schema":{"type":"object","properties":{}},
        }]},
        namespace=" Research Desk ",
    )
    manifest_inventory=kcc.scan_manifest(manifest)
    manifest_expected=kcc.capability_id("KCC"," Research Desk ","Fetch:Price%Now")
    assert manifest_expected=="kcc:research-desk:fetch%3aprice%25now"
    assert manifest_inventory["capabilities"][0]["id"]==manifest_expected

    # Reserved delimiters stay component-local instead of aliasing another ID.
    assert kcc.capability_id("mcp","a:b","c") != kcc.capability_id("mcp","a","b:c")
