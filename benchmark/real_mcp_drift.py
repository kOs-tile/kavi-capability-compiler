import asyncio
import json
import tempfile
from pathlib import Path

from kavi_capability_compiler.core import diff_inventory_lock, inventory_lock
from kavi_capability_compiler.discovery import discover_stdio

OLD="@modelcontextprotocol/server-filesystem@2026.7.10"
NEW="@modelcontextprotocol/server-filesystem@2026.8.31"


async def discover(package, allowed):
    return await discover_stdio(
        "npx",
        ["-y",package,str(allowed)],
        server_name=package,
        timeout_seconds=90.0,
    )


async def main():
    with tempfile.TemporaryDirectory(prefix="kcc-real-drift-") as tmp:
        allowed=Path(tmp)/"allowed"
        allowed.mkdir()
        before=(await discover(OLD,allowed))["inventory"]
        after=(await discover(NEW,allowed))["inventory"]
        lock=inventory_lock(before)
        drift=diff_inventory_lock(lock,after)
        out={
            "old_package":OLD,
            "new_package":NEW,
            "old_tool_count":len(before["capabilities"]),
            "new_tool_count":len(after["capabilities"]),
            "old_inventory_digest":before["digest"],
            "new_inventory_digest":after["digest"],
            "clean":drift["clean"],
            "added":drift["added"],
            "removed":drift["removed"],
            "changed":drift["changed"],
            "drift_event_count":len(drift["added"])+len(drift["removed"])+len(drift["changed"]),
        }
        print(json.dumps(out,indent=2,sort_keys=True))
        if drift["clean"]:
            raise SystemExit("Expected published-version authority drift but lock remained clean")


if __name__=="__main__":
    asyncio.run(main())
