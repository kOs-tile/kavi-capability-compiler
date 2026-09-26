import json
from collections import Counter, defaultdict
from pathlib import Path
from kavi_capability_compiler.core import classify

root=Path(__file__).parent
observed=json.loads((root/"corpus"/"observed.json").read_text())
labels=json.loads((root/"corpus"/"labels.json").read_text())
labels_by_id={r["id"]:r for r in labels}

missing=[r["id"] for r in observed if r["id"] not in labels_by_id]
extra=[r["id"] for r in labels if r["id"] not in {x["id"] for x in observed}]
if missing or extra:
    raise SystemExit(f"Corpus/label mismatch: missing={missing} extra={extra}")

rows=[]
for obs in observed:
    label=labels_by_id[obs["id"]]
    rows.append({**obs, **label})

correct=false_safe=dangerous=unknown=0
by_server=defaultdict(lambda: {"samples":0,"correct":0,"false_safe":0})
confusion=Counter(); details=[]

for r in rows:
    predicted,confidence=classify(r)
    expected=r["expected_effect"]
    ok=predicted==expected
    is_dangerous=bool(r["dangerous"])
    fs=bool(is_dangerous and predicted=="read")
    correct += int(ok); dangerous += int(is_dangerous)
    false_safe += int(fs); unknown += int(predicted=="unknown")
    confusion[(expected,predicted)] += 1
    srv=by_server[r.get("server","unknown")]
    srv["samples"]+=1; srv["correct"]+=int(ok); srv["false_safe"]+=int(fs)
    details.append({"id":r["id"],"server":r.get("server"),"name":r["name"],"expected":expected,
        "predicted":predicted,"confidence":confidence,"correct":ok,"false_safe":fs,"source":r.get("source")})

result={
    "samples":len(rows),
    "servers":len(by_server),
    "accuracy":correct/len(rows) if rows else 0,
    "dangerous_samples":dangerous,
    "false_safe_count":false_safe,
    "false_safe_rate":false_safe/dangerous if dangerous else 0,
    "unknown_rate":unknown/len(rows) if rows else 0,
    "by_server":dict(by_server),
    "confusion":{f"{a}->{b}":n for (a,b),n in sorted(confusion.items())},
    "details":details,
}
print(json.dumps(result,indent=2,sort_keys=True))
