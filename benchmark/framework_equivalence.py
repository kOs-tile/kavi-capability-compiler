import asyncio
import json

from kavi_capability_compiler.adapters import adapt_capabilities, SUPPORTED_SOURCE_FORMATS
from kavi_capability_compiler.core import compile_capsule
from kavi_capability_compiler.manifest import scan_manifest
from kavi_capability_compiler.runtime import AuthorityDenied, guarded_dispatch

GET={"type":"object","properties":{"id":{"type":"string"}},"required":["id"]}
UPDATE={"type":"object","properties":{"id":{"type":"string"},"value":{"type":"string"}},"required":["id","value"]}
DGET="Get a record by ID"
DUPDATE="Update a record"

payloads={
 "generic":{"tools":[{"name":"get_record","description":DGET,"input_schema":GET},{"name":"update_record","description":DUPDATE,"input_schema":UPDATE}]},
 "mcp":{"tools":[{"name":"get_record","description":DGET,"inputSchema":GET},{"name":"update_record","description":DUPDATE,"inputSchema":UPDATE}]},
 "openai":{"tools":[
   {"type":"function","function":{"name":"get_record","description":DGET,"parameters":GET}},
   {"type":"function","function":{"name":"update_record","description":DUPDATE,"parameters":UPDATE}},
 ]},
 "anthropic":{"tools":[{"name":"get_record","description":DGET,"input_schema":GET},{"name":"update_record","description":DUPDATE,"input_schema":UPDATE}]},
 "openapi":{"openapi":"3.1.0","paths":{
   "/records/get":{"post":{"operationId":"get_record","description":DGET,"requestBody":{"content":{"application/json":{"schema":GET}}}}},
   "/records/update":{"post":{"operationId":"update_record","description":DUPDATE,"requestBody":{"content":{"application/json":{"schema":UPDATE}}}}},
 }},
}

async def main():
    manifests={k:adapt_capabilities(k,payloads[k],namespace="records") for k in SUPPORTED_SOURCE_FORMATS}
    inventories={k:scan_manifest(v) for k,v in manifests.items()}
    manifest_digests={v["digest"] for v in manifests.values()}
    inventory_digests={v["digest"] for v in inventories.values()}

    results=[]
    for kind,inv in inventories.items():
        ids={x["name"]:x["id"] for x in inv["capabilities"]}
        cap=compile_capsule(
            inv,
            {"task":"Read one record","capabilities":[ids["get_record"]]},
            {"default":"allow"},
            now=100,
        )
        called=[]
        async def dispatcher(params):
            called.append(dict(params))
            return {"ok":True}
        allowed=await guarded_dispatch(cap,ids["get_record"],dispatcher,parameters={"id":"x"},now=101)
        before=len(called)
        blocked=False
        reason=None
        try:
            await guarded_dispatch(cap,ids["update_record"],dispatcher,parameters={"id":"x","value":"y"},now=101)
        except AuthorityDenied as exc:
            blocked=True
            reason=exc.decision["reason"]
        results.append({
            "format":kind,
            "manifest_digest":manifests[kind]["digest"],
            "inventory_digest":inv["digest"],
            "grants":[x["id"] for x in cap["grants"]],
            "allowed_executed":allowed["executed"],
            "blocked_outside_capsule":blocked,
            "blocked_reason":reason,
            "denied_dispatch_count":len(called)-before,
        })

    out={
        "formats":len(results),
        "manifest_digest_count":len(manifest_digests),
        "inventory_digest_count":len(inventory_digests),
        "all_same_grants":len({tuple(x["grants"]) for x in results})==1,
        "all_allowed_executed":all(x["allowed_executed"] for x in results),
        "all_outside_blocked":all(x["blocked_outside_capsule"] for x in results),
        "denied_dispatches_total":sum(x["denied_dispatch_count"] for x in results),
        "results":results,
    }
    print(json.dumps(out,indent=2,sort_keys=True))

if __name__=="__main__":
    asyncio.run(main())
