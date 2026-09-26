from kavi_capability_compiler.core import authorize_call, compile_capsule
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
