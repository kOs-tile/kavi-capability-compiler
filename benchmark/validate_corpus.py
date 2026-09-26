import json,re
from collections import Counter
from pathlib import Path

root=Path(__file__).parent
observed=json.loads((root/"corpus"/"observed.json").read_text())
labels=json.loads((root/"corpus"/"labels.json").read_text())
tasks=json.loads((root/"task_intents.json").read_text())

ids=[x["id"] for x in observed]
label_ids=[x["id"] for x in labels]
id_set=set(ids); label_set=set(label_ids)
duplicate_ids=sorted(k for k,v in Counter(ids).items() if v>1)
duplicate_labels=sorted(k for k,v in Counter(label_ids).items() if v>1)
identity_errors=sorted(x["id"] for x in observed if x["id"] != f'{x["server"]}:{x["name"]}')
unpinned=sorted(x["id"] for x in observed if not re.search(r"/blob/[0-9a-f]{7,40}/",x.get("source","")))
missing_sources=sorted(x["id"] for x in observed if not x.get("source"))
missing_descriptions=sorted(x["id"] for x in observed if not x.get("description"))
task_refs={cid for t in tasks for cid in t.get("required",[])+t.get("approval",[])}
missing_task_refs=sorted(task_refs-id_set)
reviewers=Counter(x.get("reviewer","missing") for x in labels)
versions=Counter(x.get("label_version","missing") for x in labels)

result={
 "capabilities":len(observed),
 "surfaces":len({x["server"] for x in observed}),
 "labels":len(labels),
 "description_coverage":(len(observed)-len(missing_descriptions))/len(observed) if observed else 0,
 "duplicate_ids":duplicate_ids,
 "duplicate_labels":duplicate_labels,
 "identity_errors":identity_errors,
 "missing_labels":sorted(id_set-label_set),
 "orphan_labels":sorted(label_set-id_set),
 "missing_sources":missing_sources,
 "unpinned_sources":unpinned,
 "missing_task_refs":missing_task_refs,
 "reviewers":dict(reviewers),
 "label_versions":dict(versions),
}
print(json.dumps(result,indent=2,sort_keys=True))

assert result["capabilities"] >= 450, result
assert result["surfaces"] >= 30, result
assert result["labels"] == result["capabilities"], result
assert result["description_coverage"] >= 0.85, result
for key in ("duplicate_ids","duplicate_labels","identity_errors","missing_labels","orphan_labels","missing_sources","unpinned_sources","missing_task_refs"):
    assert not result[key], (key,result[key])
