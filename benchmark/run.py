import json
from pathlib import Path
from kavi_capability_compiler.core import classify

rows=json.loads(Path(__file__).with_name("ground_truth.json").read_text())
correct=0; false_safe=0; dangerous=0
details=[]
for r in rows:
    predicted,confidence=classify(r)
    ok=predicted==r["expected_effect"]
    correct += int(ok)
    dangerous += int(r["dangerous"])
    # Safety failure: a dangerous tool is classified as read.
    fs=bool(r["dangerous"] and predicted=="read")
    false_safe += int(fs)
    details.append({"name":r["name"],"expected":r["expected_effect"],"predicted":predicted,"confidence":confidence,"correct":ok,"false_safe":fs})
print(json.dumps({
    "samples":len(rows),
    "accuracy":correct/len(rows),
    "dangerous_samples":dangerous,
    "false_safe_count":false_safe,
    "false_safe_rate":false_safe/dangerous if dangerous else 0,
    "details":details,
},indent=2))
