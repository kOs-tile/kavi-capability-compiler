from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from release_version import release_metadata

EXPECTED_NAME="kavi-capability-compiler"
EXPECTED_PAGES_INDEX="https://kos-tile.github.io/kavi-capability-compiler/simple/"


def require(path: str, needle: str) -> None:
    text=Path(path).read_text()
    if needle not in text:
        raise SystemExit(f"{path}: missing required release marker: {needle}")


def forbid_exact_lines(path: str, forbidden: set[str]) -> None:
    lines={line.strip() for line in Path(path).read_text().splitlines()}
    bad=sorted(lines.intersection(forbidden))
    if bad:
        raise SystemExit(f"{path}: stale unsupported install command(s): {bad}")


def main() -> None:
    metadata=release_metadata()
    version=metadata["version"]
    tag=metadata["tag"]
    project=tomllib.loads(Path("pyproject.toml").read_text())["project"]
    if project["name"] != EXPECTED_NAME:
        raise SystemExit(f"project name mismatch: {project['name']}")
    if project["requires-python"] != ">=3.11":
        raise SystemExit(f"unexpected Requires-Python: {project['requires-python']}")

    init_text=Path("src/kavi_capability_compiler/__init__.py").read_text()
    match=re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']',init_text,re.MULTILINE)
    if not match or match.group(1) != version:
        raise SystemExit("package __version__ does not match project release version")

    notes=metadata["notes"]
    direct_wheel=(
        "https://github.com/kOs-tile/kavi-capability-compiler/releases/download/"
        f"{tag}/{metadata['wheel']}"
    )
    require("CHANGELOG.md",f"## {version}")
    require(notes,f"# KAVI Capability Compiler {tag}")
    require(notes,direct_wheel)
    require("README.md",EXPECTED_PAGES_INDEX)
    require("docs/EMBEDDED_SDK.md",EXPECTED_PAGES_INDEX)
    require("docs/RELEASE_CHECKLIST.md",f"## {tag} security patch")
    require("SECURITY.md","cryptography>=50.0.1,<51")
    require("SECURITY.md","Remote Streamable HTTP discovery requires HTTPS.")

    forbid_exact_lines(
        "docs/EMBEDDED_SDK.md",
        {
            "pip install kavi-capability-compiler",
            'pip install "kavi-capability-compiler[mcp]"',
            'pip install "kavi-capability-compiler[signing]"',
            'pip install "kavi-capability-compiler[all]"',
        },
    )

    print(json.dumps({
        "validation":"kcc.release-metadata.v1",
        "name":EXPECTED_NAME,
        "version":version,
        "tag":tag,
        "requires_python":project["requires-python"],
        "release_notes":notes,
        "distribution":"github-release-first",
        "public_install_docs":"verified",
        "pass":True,
    },sort_keys=True))


if __name__=="__main__":
    main()
