import json
from collections import Counter, defaultdict
from pathlib import Path
from kavi_capability_compiler.core import classify

rows=json.loads(Path(__file__).with_name("ground_truth.json").read_text())
correct=false_safe=dangerous=unknown=0
by_server=defaultdict(lambda: {"samples":0,"correct":0,"false_safe":0})
confusion=Counter(); details=[]

for r in rows:
    predicted,confidence=classify(r)
    expected=r["expected_effect"]
    ok=predicted==expected
    is_dangerous=bool(r["dangerous"])
    # Critical safety failure: dangerous capability becomes ordinary read authority.
    fs=bool(is_dangerous and predicted=="read")
    correct += int(ok); dangerous += int(is_dangerous)
    false_safe += int(fs); unknown += int(predicted=="unknown")
    confusion[(expected,predicted)] += 1
    srv=by_server[r.get("server","unknown")]
    srv["samples"]+=1; srv["correct"]+=int(ok); srv["false_safe"]+=int(fs)
    details.append({"server":r.get("server"),"name":r["name"],"expected":expected,
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
