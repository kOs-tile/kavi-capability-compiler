import asyncio
import json
from pathlib import Path

from kavi_capability_compiler.core import inventory_lock
from kavi_capability_compiler.discovery import discover_stdio

ROOT=Path(__file__).parent
MANIFEST=json.loads((ROOT/"m2_discovery_holdout_manifest.json").read_text())


async def main():
    spec=MANIFEST["server"]
    package=f"{spec['package']}@{spec['published_version']}"
    result=await discover_stdio(
        "npx",
        ["-y",package],
        server_name="official-everything-holdout",
        timeout_seconds=90.0,
    )
    inv=result["inventory"]
    names={x["name"] for x in inv["capabilities"]}
    expected={x["name"] for x in spec["expected_tools"]}
    missing=sorted(expected-names)
    lock=inventory_lock(inv)
    out={
        "manifest_version":MANIFEST["version"],
        "package":package,
        "protocol_version":result["protocol_version"],
        "server_name":result["server"]["name"],
        "tool_count":len(inv["capabilities"]),
        "expected_tools":sorted(expected),
        "missing_expected_tools":missing,
        "inventory_digest":inv["digest"],
        "lock_digest":lock["digest"],
        "success":bool(inv["capabilities"]) and not missing,
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    if not out["success"]:
        raise SystemExit(1)


if __name__=="__main__":
    asyncio.run(main())
