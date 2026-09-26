import json
from collections import Counter, defaultdict
from pathlib import Path
from kavi_capability_compiler.core import classify

root=Path(__file__).parent/"holdout"
observed=json.loads((root/"observed.json").read_text())
labels=json.loads((root/"labels.json").read_text())
by_label={x["id"]:x for x in labels}
assert {x["id"] for x in observed} == set(by_label)

correct=false_safe=dangerous=detected=unknown=overblocked=0
confusion=Counter(); by_server=defaultdict(lambda:{"samples":0,"correct":0,"false_safe":0})
details=[]
for obs in observed:
    label=by_label[obs["id"]]
    predicted,confidence=classify(obs)
    expected=label["expected_effect"]; is_dangerous=bool(label["dangerous"])
    ok=predicted==expected; fs=is_dangerous and predicted=="read"
    correct+=int(ok); dangerous+=int(is_dangerous); detected+=int(is_dangerous and predicted!="read")
    false_safe+=int(fs); unknown+=int(predicted=="unknown")
    overblocked+=int((not is_dangerous) and predicted in {"delete","execute","financial","deploy","write","external_message"})
    confusion[(expected,predicted)]+=1
    s=by_server[obs["server"]]; s["samples"]+=1; s["correct"]+=int(ok); s["false_safe"]+=int(fs)
    details.append({"id":obs["id"],"expected":expected,"predicted":predicted,"confidence":confidence,"dangerous":is_dangerous,"correct":ok,"false_safe":fs})

safe=len(observed)-dangerous
result={
 "samples":len(observed),"servers":len(by_server),"accuracy":correct/len(observed),
 "dangerous_samples":dangerous,"dangerous_recall":detected/dangerous if dangerous else 0,
 "false_safe_count":false_safe,"false_safe_rate":false_safe/dangerous if dangerous else 0,
 "unknown_rate":unknown/len(observed),"overblocking_rate":overblocked/safe if safe else 0,
 "by_server":dict(by_server),
 "confusion":{f"{a}->{b}":n for (a,b),n in sorted(confusion.items())},
 "details":details,
}
print(json.dumps(result,indent=2,sort_keys=True))
