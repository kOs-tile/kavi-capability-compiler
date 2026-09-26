import json
from pathlib import Path

root=Path(__file__).parent
observed=json.loads((root/"corpus"/"observed.json").read_text())
tasks=json.loads((root/"task_intents.json").read_text())
available={x["id"] for x in observed}
rows=[]
for t in tasks:
    required=t["required"]
    missing=[x for x in required if x not in available]
    if missing:
        raise SystemExit(f"Task {t['id']} references missing capabilities: {missing}")
    exposed=len(available)
    granted=len(set(required))
    approvals=len(set(t.get("approval",[])))
    rows.append({
        "task":t["id"],"available":exposed,"required":granted,
        "authority_reduction":1-(granted/exposed),
        "approval_burden":approvals/granted if granted else 0,
    })
result={
    "tasks":len(rows),
    "inventory_capabilities":len(available),
    "mean_required_capabilities":sum(x["required"] for x in rows)/len(rows),
    "mean_authority_reduction":sum(x["authority_reduction"] for x in rows)/len(rows),
    "mean_approval_burden":sum(x["approval_burden"] for x in rows)/len(rows),
    "details":rows,
}
print(json.dumps(result,indent=2,sort_keys=True))
