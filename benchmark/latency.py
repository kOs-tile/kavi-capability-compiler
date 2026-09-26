import json,time,statistics
from pathlib import Path
from kavi_capability_compiler.core import scan_mcp_snapshot,compile_capsule,authorize_call

rows=json.loads((Path(__file__).parent/"corpus"/"observed.json").read_text())
tools=[{"name":r["name"],"description":r.get("description",""),"inputSchema":r.get("inputSchema") or {},
        "annotations":r.get("annotations") or {}} for r in rows]
inv=scan_mcp_snapshot({"server":{"name":"latency-bench"},"tools":tools})
ids=[c["id"] for c in inv["capabilities"][:3]]
intent={"task":"latency benchmark","capabilities":ids}
policy={"default":"allow"}

compile_ns=[]
for i in range(5000):
    t=time.perf_counter_ns(); cap=compile_capsule(inv,intent,policy,now=100+i); compile_ns.append(time.perf_counter_ns()-t)
cap=compile_capsule(inv,intent,policy,now=100)
auth_ns=[]
for _ in range(10000):
    t=time.perf_counter_ns(); authorize_call(cap,ids[0],now=101); auth_ns.append(time.perf_counter_ns()-t)

def stats(xs):
    ys=sorted(x/1e6 for x in xs)
    return {"median_ms":statistics.median(ys),"p95_ms":ys[int(len(ys)*0.95)-1],"p99_ms":ys[int(len(ys)*0.99)-1]}
print(json.dumps({"inventory_capabilities":len(inv["capabilities"]),"compile":stats(compile_ns),"authorize":stats(auth_ns)},indent=2,sort_keys=True))
