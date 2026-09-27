from __future__ import annotations

import html
import re
import sys
from pathlib import Path

PROJECT="kavi-capability-compiler"
VERSION="0.1.0"
TAG="v0.1.0"
REQUIRES_PYTHON=">=3.11"
RELEASE_BASE=f"https://github.com/kOs-tile/kavi-capability-compiler/releases/download/{TAG}"
HEX64=re.compile(r"^[0-9a-f]{64}$")


def read_checksums(dist: Path) -> dict[str,str]:
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
    expected=[
        name for name in rows
        if name.endswith(".whl") or name.endswith(".tar.gz")
    ]
    wheels=[name for name in expected if name.endswith(".whl")]
    sdists=[name for name in expected if name.endswith(".tar.gz")]
    if len(wheels)!=1 or len(sdists)!=1 or len(rows)!=2:
        raise ValueError("expected exactly one wheel and one sdist checksum")
    if not wheels[0].startswith("kavi_capability_compiler-0.1.0-"):
        raise ValueError(f"unexpected wheel filename: {wheels[0]}")
    if sdists[0]!="kavi_capability_compiler-0.1.0.tar.gz":
        raise ValueError(f"unexpected sdist filename: {sdists[0]}")
    return rows


def build(dist: Path, site: Path) -> None:
    checksums=read_checksums(dist)
    project_dir=site/"simple"/PROJECT
    project_dir.mkdir(parents=True,exist_ok=True)

    root="""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>KCC Simple Index</title></head>
<body><a href="./kavi-capability-compiler/">kavi-capability-compiler</a></body></html>
"""
    (site/"simple"/"index.html").write_text(root)

    links=[]
    for name,digest in sorted(checksums.items()):
        safe_name=html.escape(name,quote=True)
        url=f"{RELEASE_BASE}/{name}#sha256={digest}"
        links.append(
            f'<a href="{html.escape(url,quote=True)}" '
            f'data-requires-python="{html.escape(REQUIRES_PYTHON,quote=True)}">'
            f'{safe_name}</a>'
        )
    detail=(
        '<!DOCTYPE html>\n<html><head><meta charset="utf-8">'
        '<title>kavi-capability-compiler</title></head><body>\n'
        + "\n".join(links)
        + "\n</body></html>\n"
    )
    (project_dir/"index.html").write_text(detail)
    (site/".nojekyll").write_text("")

    landing=f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>KAVI Capability Compiler</title></head>
<body>
<h1>KAVI Capability Compiler {VERSION}</h1>
<p>Framework-agnostic least-authority compiler for AI agent systems.</p>
<pre>python -m pip install --index-url https://kos-tile.github.io/kavi-capability-compiler/simple/ kavi-capability-compiler</pre>
<p><a href="./simple/">Simple Repository API</a></p>
</body></html>
"""
    (site/"index.html").write_text(landing)


def main() -> None:
    if len(sys.argv)!=3:
        raise SystemExit("usage: build_simple_index.py DIST_DIR SITE_DIR")
    build(Path(sys.argv[1]),Path(sys.argv[2]))


if __name__=="__main__":
    main()
