import json
from pathlib import Path

from kavi_capability_compiler.core import authorize_call, compile_capsule
from kavi_capability_compiler.kavi_dispatch import scan_kavi_dispatch_contract

root=Path(__file__).parent/"kavi_dogfood"
raw=json.loads((root/"dispatch_contract.json").read_text())
source=raw["source"]
inv=scan_kavi_dispatch_contract(
    raw["contract"],
    source_repository=source["repository"],
    source_path=source["path"],
    source_sha=source["sha"],
)
ids={x["name"]:x["id"] for x in inv["capabilities"]}
writes=[x for x in inv["capabilities"] if x["effect"]=="write"]
intent={
    "task":"Read the current KAVI operator snapshot without mutating execution state",
    "ttl_seconds":300,
    "capabilities":[ids["get_operator_snapshot"]],
}
policy={
    "default":"deny",
    "allow":[{"capabilities":[ids["get_operator_snapshot"]]}],
    "deny":[{"effects":["write","delete","execute","deploy","financial","external_message"]}],
}
cap=compile_capsule(inv,intent,policy,now=100)
checks={
    "granted_read":authorize_call(cap,ids["get_operator_snapshot"],parameters={},now=101),
    "blocked_enqueue":authorize_call(cap,ids["enqueue_task"],parameters={},now=101),
    "blocked_approval":authorize_call(cap,ids["approve_task"],parameters={},now=101),
}
result={
    "source":source,
    "inventory_capabilities":len(inv["capabilities"]),
    "declared_mutations":len(writes),
    "compiled_grants":len(cap["grants"]),
    "authority_reduction":1-(len(cap["grants"])/len(inv["capabilities"])),
    "capsule_status":cap["status"],
    "allowed_inside_capsule":checks["granted_read"]["allowed"],
    "enqueue_blocked":not checks["blocked_enqueue"]["allowed"],
    "approve_blocked":not checks["blocked_approval"]["allowed"],
    "enqueue_reason":checks["blocked_enqueue"]["reason"],
    "approve_reason":checks["blocked_approval"]["reason"],
    "mutation_grants":[x["id"] for x in cap["grants"] if x["effect"]=="write"],
}
print(json.dumps(result,indent=2,sort_keys=True))
