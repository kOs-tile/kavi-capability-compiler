from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from release_version import release_metadata

PROJECT="kavi-capability-compiler"
REQUIRES_PYTHON=">=3.11"
HEX64=re.compile(r"^[0-9a-f]{64}$")


def read_checksums(dist: Path) -> dict[str,str]:
    metadata=release_metadata()
    rows={}
    for raw in (dist/"SHA256SUMS").read_text().splitlines():
        if not raw.strip():
            continue
        parts=raw.split(None,1)
        if len(parts)!=2:
            raise ValueError(f"invalid checksum row: {raw!r}")
        digest,name=parts
        name=name.lstrip("*").strip()
        if Path(name).name != name:
            raise ValueError(f"unsafe artifact filename: {name!r}")
        if not HEX64.fullmatch(digest):
            raise ValueError(f"invalid sha256 for {name}")
        if name in rows:
            raise ValueError(f"duplicate checksum entry: {name}")
        if not (dist/name).is_file():
            raise ValueError(f"checksum references missing artifact: {name}")
        rows[name]=digest
    wheels=[name for name in rows if name.endswith(".whl")]
    sdists=[name for name in rows if name.endswith(".tar.gz")]
    if len(wheels)!=1 or len(sdists)!=1 or len(rows)!=2:
        raise ValueError("expected exactly one wheel and one sdist checksum")
    if wheels[0] != metadata["wheel"]:
        raise ValueError(f"unexpected wheel filename: {wheels[0]}")
    if sdists[0] != metadata["sdist"]:
        raise ValueError(f"unexpected sdist filename: {sdists[0]}")
    return rows


def build(dist: Path, site: Path) -> None:
    metadata=release_metadata()
    release_base="https://github.com/kOs-tile/kavi-capability-compiler/releases/download/"+metadata["tag"]
    checksums=read_checksums(dist)
    project_dir=site/"simple"/PROJECT
    project_dir.mkdir(parents=True,exist_ok=True)

    (site/"simple"/"index.html").write_text(
        '<!DOCTYPE html>\n<html><head><meta charset="utf-8"><title>KCC Simple Index</title></head>\n'
        '<body><a href="./kavi-capability-compiler/">kavi-capability-compiler</a></body></html>\n'
    )

    links=[]
    for name,digest in sorted(checksums.items()):
        url=f"{release_base}/{name}#sha256={digest}"
        links.append(
            f'<a href="{html.escape(url,quote=True)}" '
            f'data-requires-python="{html.escape(REQUIRES_PYTHON,quote=True)}">'
            f'{html.escape(name,quote=True)}</a>'
        )
    (project_dir/"index.html").write_text(
        '<!DOCTYPE html>\n<html><head><meta charset="utf-8"><title>kavi-capability-compiler</title></head><body>\n'
        + "\n".join(links)
        + "\n</body></html>\n"
    )
    (site/".nojekyll").write_text("")
    (site/"index.html").write_text(
        '<!DOCTYPE html>\n<html><head><meta charset="utf-8"><title>KAVI Capability Compiler</title></head>\n'
        f'<body><h1>KAVI Capability Compiler {metadata["version"]}</h1>\n'
        '<p>Framework-agnostic least-authority compiler for AI agent systems.</p>\n'
        '<pre>python -m pip install --index-url https://kos-tile.github.io/kavi-capability-compiler/simple/ kavi-capability-compiler</pre>\n'
        '<p><a href="./simple/">Simple Repository API</a></p></body></html>\n'
    )


def main() -> None:
    if len(sys.argv)!=3:
        raise SystemExit("usage: build_simple_index.py DIST_DIR SITE_DIR")
    build(Path(sys.argv[1]),Path(sys.argv[2]))


if __name__=="__main__":
    main()
