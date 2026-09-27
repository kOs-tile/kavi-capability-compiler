from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifacts(directory: Path) -> dict[str, Path]:
    rows={}
    for pattern in ("*.whl","*.tar.gz"):
        matches=sorted(directory.glob(pattern))
        if len(matches) != 1:
            raise SystemExit(f"{directory}: expected exactly one {pattern}, found {len(matches)}")
        rows[matches[0].name]=matches[0]
    return rows


def verify_wheel_surface(wheel: Path) -> dict[str, object]:
    with zipfile.ZipFile(wheel) as archive:
        names=sorted(archive.namelist())
    roots=sorted({name.split("/",1)[0] for name in names if name and "/" in name})
    forbidden=(
        "case_studies/",
        "examples/",
        "benchmark/",
        "tests/",
        "docs/",
        "scripts/",
        "schemas/",
    )
    leaks=sorted(name for name in names if name.startswith(forbidden))
    if leaks:
        raise SystemExit(f"wheel contains repository-only paths: {leaks[:10]}")
    unexpected=[
        root for root in roots
        if root!="kavi_capability_compiler"
        and not (root.startswith("kavi_capability_compiler-") and root.endswith(".dist-info"))
    ]
    if unexpected:
        raise SystemExit(f"wheel contains unexpected top-level roots: {unexpected}")
    if "kavi_capability_compiler" not in roots:
        raise SystemExit("wheel is missing kavi_capability_compiler package")
    return {
        "roots":roots,
        "file_count":len(names),
        "repository_only_leaks":0,
    }


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: verify_reproducible_builds.py DIST_A DIST_B")
    left=artifacts(Path(sys.argv[1]))
    right=artifacts(Path(sys.argv[2]))
    if set(left) != set(right):
        raise SystemExit(f"artifact filenames differ: {sorted(left)} != {sorted(right)}")

    rows={}
    for name in sorted(left):
        first=sha256(left[name])
        second=sha256(right[name])
        rows[name]={"sha256":first,"match":first==second}
        if first != second:
            print(json.dumps({"pass":False,"artifacts":rows},sort_keys=True))
            raise SystemExit(f"non-reproducible artifact: {name}")

    wheel=next(path for name,path in left.items() if name.endswith(".whl"))
    surface=verify_wheel_surface(wheel)
    result={
        "validation":"kcc.release-reproducibility.v1",
        "artifacts":rows,
        "wheel_surface":surface,
        "pass":True,
    }
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
