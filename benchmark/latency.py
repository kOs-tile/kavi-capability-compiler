import json,time,statistics
from pathlib import Path
import kavi_capability_compiler as kcc

rows=json.loads((Path(__file__).parent/"corpus"/"observed.json").read_text())
tools=[{
    "namespace":r.get("server") or "latency-bench",
    "name":r["name"],
    "description":r.get("description",""),
    "input_schema":r.get("inputSchema") or {},
    "annotations":r.get("annotations") or {},
} for r in rows]
manifest=kcc.adapt_capabilities(
    "generic",
    {"tools":tools},
    namespace="latency-bench",
)
inv=kcc.scan_manifest(manifest)
ids=[c["id"] for c in inv["capabilities"][:3]]
intent={"task":"latency benchmark","capabilities":ids}
policy={"default":"allow"}

compile_ns=[]
for i in range(5000):
    t=time.perf_counter_ns(); cap=kcc.compile_capsule(inv,intent,policy,now=100+i); compile_ns.append(time.perf_counter_ns()-t)
cap=kcc.compile_capsule(inv,intent,policy,now=100)
auth_ns=[]
for _ in range(10000):
    t=time.perf_counter_ns(); kcc.authorize_call(cap,ids[0],now=101); auth_ns.append(time.perf_counter_ns()-t)

def stats(xs):
    ys=sorted(x/1e6 for x in xs)
    return {"median_ms":statistics.median(ys),"p95_ms":ys[int(len(ys)*0.95)-1],"p99_ms":ys[int(len(ys)*0.99)-1]}
print(json.dumps({"inventory_capabilities":len(inv["capabilities"]),"compile":stats(compile_ns),"authorize":stats(auth_ns)},indent=2,sort_keys=True))
