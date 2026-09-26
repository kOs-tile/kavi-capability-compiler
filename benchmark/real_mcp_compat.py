import asyncio
import json
import tempfile
from pathlib import Path

from kavi_capability_compiler.core import inventory_lock
from kavi_capability_compiler.discovery import discover_stdio

SERVERS = [
    {
        "id": "filesystem",
        "package": "@modelcontextprotocol/server-filesystem@0.6.3",
        "expected": {"read_text_file", "write_file", "list_directory"},
    },
    {
        "id": "memory",
        "package": "@modelcontextprotocol/server-memory@0.6.3",
        "expected": {"read_graph", "create_entities", "delete_entities"},
    },
    {
        "id": "sequential-thinking",
        "package": "@modelcontextprotocol/server-sequential-thinking@0.6.2",
        "expected": {"sequential_thinking"},
    },
]


async def discover_one(spec, root):
    args=["-y", spec["package"]]
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
    missing=sorted(spec["expected"]-names)
    if missing:
        raise AssertionError(f"{spec['id']} missing expected tools: {missing}")
    lock=inventory_lock(inv)
    return {
        "id":spec["id"],
        "package":spec["package"],
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
        for spec in SERVERS:
            results.append(await discover_one(spec,root))
        print(json.dumps({
            "servers":len(results),
            "all_nonempty":all(x["tool_count"]>0 for x in results),
            "all_expected_tools_present":all(x["expected_tools_present"] for x in results),
            "results":results,
        },indent=2,sort_keys=True))


if __name__=="__main__":
    asyncio.run(main())
