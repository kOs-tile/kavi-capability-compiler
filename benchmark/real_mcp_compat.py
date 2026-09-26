import asyncio
import json
import tempfile
from pathlib import Path

from kavi_capability_compiler.core import inventory_lock
from kavi_capability_compiler.discovery import discover_stdio

ROOT=Path(__file__).parent
MANIFEST=json.loads((ROOT/"real_mcp_compat_manifest.json").read_text())


async def discover_one(spec, root):
    package_spec=f"{spec['package']}@{spec['published_version']}"
    args=["-y", package_spec]
    env={}
    if spec["id"]=="filesystem":
        allowed=root/"filesystem"
        allowed.mkdir()
        args.append(str(allowed))
    elif spec["id"]=="memory":
        env["MEMORY_FILE_PATH"]=str(root/"memory.jsonl")
    elif spec["id"]=="sequential-thinking":
        env["DISABLE_THOUGHT_LOGGING"]="true"

    result=await discover_stdio(
        "npx",
        args,
        env=env,
        server_name=f"official-{spec['id']}",
        timeout_seconds=90.0,
    )
    inv=result["inventory"]
    names={c["name"] for c in inv["capabilities"]}
    expected=set(spec["expected_tools"])
    missing=sorted(expected-names)
    if missing:
        raise AssertionError(f"{spec['id']} missing expected tools: {missing}")
    lock=inventory_lock(inv)
    return {
        "id":spec["id"],
        "package":package_spec,
        "source_repository":spec["source_repository"],
        "source_blob_sha":spec["source_blob_sha"],
        "protocol_version":result["protocol_version"],
        "server_name":result["server"]["name"],
        "tool_count":len(inv["capabilities"]),
        "inventory_digest":inv["digest"],
        "lock_digest":lock["digest"],
        "expected_tools_present":True,
    }


async def main():
    with tempfile.TemporaryDirectory(prefix="kcc-real-mcp-") as tmp:
        root=Path(tmp)
        results=[]
        for spec in MANIFEST["servers"]:
            results.append(await discover_one(spec,root))
        print(json.dumps({
            "manifest_version":MANIFEST["version"],
            "servers":len(results),
            "all_nonempty":all(x["tool_count"]>0 for x in results),
            "all_expected_tools_present":all(x["expected_tools_present"] for x in results),
            "results":results,
        },indent=2,sort_keys=True))


if __name__=="__main__":
    asyncio.run(main())
