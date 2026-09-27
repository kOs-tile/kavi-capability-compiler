from __future__ import annotations

import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    dist=Path("dist")
    artifacts=sorted([*dist.glob("*.whl"),*dist.glob("*.tar.gz")],key=lambda p:p.name)
    if not artifacts:
        raise SystemExit("no release artifacts found")
    lines=[f"{sha256(path)}  {path.name}" for path in artifacts]
    (dist/"SHA256SUMS").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))


if __name__=="__main__":
    main()
