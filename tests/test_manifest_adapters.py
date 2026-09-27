from kavi_capability_compiler.core import authorize_call, compile_capsule, digest
from kavi_capability_compiler.manifest import (
    build_manifest,
    from_anthropic_tools,
    from_generic,
    from_mcp_tools,
    from_openai_tools,
    from_openapi,
    scan_manifest,
)

SCHEMA_GET={"type":"object","properties":{"id":{"type":"string"}},"required":["id"]}
SCHEMA_UPDATE={
    "type":"object",
    "properties":{"id":{"type":"string"},"value":{"type":"string"}},
    "required":["id","value"],
}
DESC_GET="Get a record by ID"
DESC_UPDATE="Update a record"


def _formats():
    generic=from_generic([
        {"name":"get_record","description":DESC_GET,"input_schema":SCHEMA_GET},
        {"name":"update_record","description":DESC_UPDATE,"input_schema":SCHEMA_UPDATE},
    ],namespace="records")

    mcp=from_mcp_tools([
        {"name":"get_record","description":DESC_GET,"inputSchema":SCHEMA_GET},
        {"name":"update_record","description":DESC_UPDATE,"inputSchema":SCHEMA_UPDATE},
    ],namespace="records",server="demo")

    openai=from_openai_tools([
        {"type":"function","function":{"name":"get_record","description":DESC_GET,"parameters":SCHEMA_GET}},
        {"type":"function","function":{"name":"update_record","description":DESC_UPDATE,"parameters":SCHEMA_UPDATE}},
    ],namespace="records")

    anthropic=from_anthropic_tools([
        {"name":"get_record","description":DESC_GET,"input_schema":SCHEMA_GET},
        {"name":"update_record","description":DESC_UPDATE,"input_schema":SCHEMA_UPDATE},
    ],namespace="records")

    openapi=from_openapi({
        "openapi":"3.1.0",
        "paths":{
            "/records/get":{"post":{
                "operationId":"get_record",
                "description":DESC_GET,
                "requestBody":{"content":{"application/json":{"schema":SCHEMA_GET}}},
            }},
            "/records/update":{"post":{
                "operationId":"update_record",
                "description":DESC_UPDATE,
                "requestBody":{"content":{"application/json":{"schema":SCHEMA_UPDATE}}},
            }},
        },
    },namespace="records")

    return [generic,mcp,openai,anthropic,openapi]


def test_equivalent_framework_formats_produce_same_semantic_manifest():
    manifests=_formats()
    assert len({m["digest"] for m in manifests})==1
    fingerprints=[
        [(x["namespace"],x["name"],x["fingerprint"]) for x in m["capabilities"]]
        for m in manifests
    ]
    assert all(x==fingerprints[0] for x in fingerprints[1:])
    assert len({tuple(x["source"]["kind"] for x in m["capabilities"]) for m in manifests})==5


def test_equivalent_framework_formats_produce_same_inventory_and_capsule_boundary():
    inventories=[scan_manifest(m) for m in _formats()]
    assert len({x["digest"] for x in inventories})==1
    ids={x["name"]:x["id"] for x in inventories[0]["capabilities"]}
    intent={"task":"Read one record","capabilities":[ids["get_record"]]}
    policy={
        "default":"deny",
        "allow":[{"capabilities":[ids["get_record"]]}],
        "deny":[{"effects":["write","delete","execute","deploy","financial","external_message"]}],
    }
    capsules=[compile_capsule(inv,intent,policy,now=100) for inv in inventories]
    assert all(c["status"]=="ready" for c in capsules)
    assert all([g["id"] for g in c["grants"]]==[ids["get_record"]] for c in capsules)
    for cap in capsules:
        assert authorize_call(cap,ids["get_record"],parameters={"id":"a"},now=101)["allowed"]
        assert authorize_call(cap,ids["update_record"],parameters={"id":"a","value":"b"},now=101)["reason"]=="capability_not_granted"


def test_provenance_only_change_does_not_change_semantic_authority():
    a=from_generic([
        {"name":"get_record","description":DESC_GET,"input_schema":SCHEMA_GET},
    ],namespace="records",source_metadata={"file":"one.json","revision":"a"})
    b=from_generic([
        {"name":"get_record","description":DESC_GET,"input_schema":SCHEMA_GET},
    ],namespace="records",source_metadata={"file":"two.json","revision":"b"})
    assert a["digest"]==b["digest"]
    assert a["capabilities"][0]["fingerprint"]==b["capabilities"][0]["fingerprint"]


def test_schema_change_changes_only_affected_capability_fingerprint():
    a=from_generic([
        {"name":"get_record","description":DESC_GET,"input_schema":SCHEMA_GET},
        {"name":"update_record","description":DESC_UPDATE,"input_schema":SCHEMA_UPDATE},
    ],namespace="records")
    changed=dict(SCHEMA_UPDATE)
    changed={"type":"object","properties":{**SCHEMA_UPDATE["properties"],"force":{"type":"boolean"}},"required":["id","value"]}
    b=from_generic([
        {"name":"get_record","description":DESC_GET,"input_schema":SCHEMA_GET},
        {"name":"update_record","description":DESC_UPDATE,"input_schema":changed},
    ],namespace="records")
    afp={x["name"]:x["fingerprint"] for x in a["capabilities"]}
    bfp={x["name"]:x["fingerprint"] for x in b["capabilities"]}
    assert afp["get_record"]==bfp["get_record"]
    assert afp["update_record"]!=bfp["update_record"]
    assert a["digest"]!=b["digest"]


def test_same_tool_name_in_different_namespaces_does_not_collide():
    m=from_generic([
        {"namespace":"github","name":"search","description":"Search GitHub","input_schema":{"type":"object"}},
        {"namespace":"slack","name":"search","description":"Search Slack","input_schema":{"type":"object"}},
    ])
    inv=scan_manifest(m)
    ids=sorted(x["id"] for x in inv["capabilities"])
    assert ids==["kcc:github:search","kcc:slack:search"]


def test_duplicate_identity_in_same_namespace_fails_closed():
    try:
        from_generic([
            {"name":"search","description":"A"},
            {"name":"search","description":"B"},
        ],namespace="same")
        assert False, "expected duplicate identity failure"
    except ValueError as exc:
        assert "Duplicate capability identity" in str(exc)


import asyncio
from kavi_capability_compiler.adapters import adapt_capabilities, SUPPORTED_SOURCE_FORMATS
from kavi_capability_compiler.runtime import AuthorityDenied, guarded_dispatch


def test_adapter_dispatch_contract_supports_all_declared_formats():
    payloads={
        "generic":{"tools":[{"name":"get_record","description":DESC_GET,"input_schema":SCHEMA_GET}]},
        "mcp":{"tools":[{"name":"get_record","description":DESC_GET,"inputSchema":SCHEMA_GET}]},
        "openai":{"tools":[{"type":"function","function":{"name":"get_record","description":DESC_GET,"parameters":SCHEMA_GET}}]},
        "anthropic":{"tools":[{"name":"get_record","description":DESC_GET,"input_schema":SCHEMA_GET}]},
        "openapi":{"openapi":"3.1.0","paths":{"/records/get":{"post":{"operationId":"get_record","description":DESC_GET,"requestBody":{"content":{"application/json":{"schema":SCHEMA_GET}}}}}}},
    }
    manifests=[adapt_capabilities(kind,payloads[kind],namespace="records") for kind in SUPPORTED_SOURCE_FORMATS]
    assert len({m["digest"] for m in manifests})==1


def test_generic_runtime_guard_is_source_format_independent():
    manifests=_formats()
    dispatched=[]
    async def dispatcher(params):
        dispatched.append(dict(params))
        return {"ok":True}

    for manifest in manifests:
        inv=scan_manifest(manifest)
        ids={x["name"]:x["id"] for x in inv["capabilities"]}
        cap=compile_capsule(
            inv,
            {"task":"Read one record","capabilities":[ids["get_record"]]},
            {"default":"allow"},
            now=100,
        )
        out=asyncio.run(guarded_dispatch(
            cap,ids["get_record"],dispatcher,parameters={"id":"a"},now=101
        ))
        assert out["executed"] is True
        before=len(dispatched)
        try:
            asyncio.run(guarded_dispatch(
                cap,ids["update_record"],dispatcher,parameters={"id":"a","value":"b"},now=101
            ))
            assert False, "expected AuthorityDenied"
        except AuthorityDenied as exc:
            assert exc.decision["reason"]=="capability_not_granted"
        assert len(dispatched)==before


def test_manifest_cli_round_trip(tmp_path):
    import json
    import subprocess
    import sys

    source=tmp_path/"tools.json"
    manifest_path=tmp_path/"capabilities.json"
    inventory_path=tmp_path/"inventory.json"
    source.write_text(json.dumps({
        "tools":[
            {"type":"function","function":{
                "name":"get_record",
                "description":DESC_GET,
                "parameters":SCHEMA_GET,
            }}
        ]
    }))
    code="from kavi_capability_compiler import cli; cli.main()"
    p1=subprocess.run(
        [sys.executable,"-c",code,"manifest",str(source),"--format","openai","--namespace","records","-o",str(manifest_path)],
        capture_output=True,text=True,timeout=15,
    )
    assert p1.returncode==0, p1.stderr
    manifest=json.loads(manifest_path.read_text())
    assert manifest["schema_version"]=="kcc.capabilities.v1"
    assert manifest["capabilities"][0]["source"]["kind"]=="openai-function"

    p2=subprocess.run(
        [sys.executable,"-c",code,"scan-manifest",str(manifest_path),"-o",str(inventory_path)],
        capture_output=True,text=True,timeout=15,
    )
    assert p2.returncode==0, p2.stderr
    inventory=json.loads(inventory_path.read_text())
    assert inventory["adapter"]=="universal-manifest.v1"
    assert [x["id"] for x in inventory["capabilities"]]==["kcc:records:get_record"]


def test_tampered_manifest_fingerprint_fails_closed():
    manifest=from_generic([
        {"name":"get_record","description":DESC_GET,"input_schema":SCHEMA_GET},
    ],namespace="records")
    manifest["capabilities"][0]["description"]="Tampered authority description"
    try:
        scan_manifest(manifest)
        assert False, "expected fingerprint mismatch"
    except ValueError as exc:
        assert "fingerprint mismatch" in str(exc).lower()


def test_unsupported_adapter_format_fails_closed():
    from kavi_capability_compiler.adapters import adapt_capabilities
    try:
        adapt_capabilities("unknown-framework",{"tools":[]},namespace="x")
        assert False, "expected unsupported format failure"
    except ValueError as exc:
        assert "Unsupported capability source format" in str(exc)

def test_manifest_digest_is_enforced_even_if_capability_fingerprint_is_recomputed():
    manifest=from_generic([
        {"name":"get_record","description":DESC_GET,"input_schema":SCHEMA_GET},
    ],namespace="records")
    manifest["capabilities"][0]["description"]="Changed authority semantics"
    semantic={
        "namespace":"records",
        "name":"get_record",
        "description":"Changed authority semantics",
        "input_schema":SCHEMA_GET,
        "annotations":{},
    }
    manifest["capabilities"][0]["fingerprint"]=digest(semantic)
    try:
        scan_manifest(manifest)
        assert False, "expected manifest digest mismatch"
    except ValueError as exc:
        assert "manifest digest mismatch" in str(exc).lower()


def test_manifest_missing_digest_fails_closed():
    manifest=from_generic([
        {"name":"get_record","description":DESC_GET,"input_schema":SCHEMA_GET},
    ],namespace="records")
    manifest.pop("digest")
    try:
        scan_manifest(manifest)
        assert False, "expected manifest digest mismatch"
    except ValueError as exc:
        assert "manifest digest mismatch" in str(exc).lower()


def test_manifest_rejects_canonical_identity_aliases():
    try:
        from_generic([
            {"namespace":"records","name":"Read Item","description":"Read"},
            {"namespace":"records","name":"read-item","description":"Read alias"},
        ])
        assert False, "expected canonical identity collision"
    except ValueError as exc:
        assert "Duplicate canonical capability identity" in str(exc)
