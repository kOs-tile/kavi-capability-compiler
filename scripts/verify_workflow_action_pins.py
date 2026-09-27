from __future__ import annotations

import re
import sys
from pathlib import Path

USES_RE=re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)")
PINNED_ACTION_RE=re.compile(r"^[^@\s]+@[0-9a-fA-F]{40}$")


def verify(root: Path) -> list[str]:
    violations=[]
    files=sorted(list(root.rglob("*.yml"))+list(root.rglob("*.yaml")))
    for path in files:
        for lineno,line in enumerate(path.read_text().splitlines(),1):
            match=USES_RE.match(line)
            if not match:
                continue
            target=match.group(1).strip("'\"")
            if target.startswith("./"):
                continue
            if target.startswith("docker://"):
                if "@sha256:" not in target:
                    violations.append(f"{path}:{lineno}: mutable container action: {target}")
                continue
            if not PINNED_ACTION_RE.fullmatch(target):
                violations.append(f"{path}:{lineno}: mutable action reference: {target}")
    return violations


def main() -> None:
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(".github/workflows")
    violations=verify(root)
    if violations:
        for row in violations:
            print(row)
        raise SystemExit(1)
    print("KCC_WORKFLOW_ACTION_PINS: PASS")


if __name__=="__main__":
    main()
