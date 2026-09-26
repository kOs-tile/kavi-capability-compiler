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
        "__version__","SDK_VERSION","SCHEMA_VERSION","SUPPORTED_SOURCE_FORMATS",
        "adapt_capabilities","build_manifest","scan_manifest","compile_capsule",
        "verify_capsule","authorize_call","inventory_lock","diff_inventory_lock",
        "Guard","AuthorityDenied","ApprovalRequired","CapabilityDenied",
    }
    assert set(kcc.__all__)==expected
    assert not any("kavi" in name.lower() or "hermes" in name.lower() or "codex" in name.lower() for name in kcc.__all__)
