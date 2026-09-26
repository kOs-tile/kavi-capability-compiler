import json
from pathlib import Path
from kavi_capability_compiler.core import scan_mcp_snapshot, inventory_lock, diff_inventory_lock

rows=json.loads((Path(__file__).parent/"corpus"/"observed.json").read_text())
by_server={}
for r in rows:
    by_server.setdefault(r["server"],[]).append({
        "name":r["name"],"description":r.get("description",""),
        "inputSchema":r.get("inputSchema") or {}, "annotations":r.get("annotations") or {}
    })

expected=detected=0
details=[]
for server,tools in sorted(by_server.items()):
    if not tools: continue
    base=scan_mcp_snapshot({"server":{"name":server},"tools":tools})
    lock=inventory_lock(base)

    changed=json.loads(json.dumps(tools))
    changed[0]["description"]=changed[0].get("description","")+" [drift]"
    d=diff_inventory_lock(lock,scan_mcp_snapshot({"server":{"name":server},"tools":changed}))
    expected+=1; detected+=int(bool(d["changed"]))
    details.append({"server":server,"mutation":"changed","detected":bool(d["changed"])})

    removed=tools[1:] if len(tools)>1 else []
    d=diff_inventory_lock(lock,scan_mcp_snapshot({"server":{"name":server},"tools":removed}))
    expected+=1; detected+=int(bool(d["removed"]))
    details.append({"server":server,"mutation":"removed","detected":bool(d["removed"])})

    added=tools+[{"name":"__kcc_drift_probe__","description":"Synthetic benchmark probe","inputSchema":{"type":"object"}}]
    d=diff_inventory_lock(lock,scan_mcp_snapshot({"server":{"name":server},"tools":added}))
    expected+=1; detected+=int(bool(d["added"]))
    details.append({"server":server,"mutation":"added","detected":bool(d["added"])})

result={"servers":len(by_server),"expected_events":expected,"detected_events":detected,
        "drift_recall":detected/expected if expected else 0,"details":details}
print(json.dumps(result,indent=2,sort_keys=True))
