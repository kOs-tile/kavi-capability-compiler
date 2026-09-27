from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

EXPECTED_NAME="kavi-capability-compiler"
EXPECTED_VERSION="0.1.0"
EXPECTED_TAG="v0.1.0"
EXPECTED_DIRECT_WHEEL=(
    "https://github.com/kOs-tile/kavi-capability-compiler/releases/download/"
    "v0.1.0/kavi_capability_compiler-0.1.0-py3-none-any.whl"
)


def require(path: str, needle: str) -> None:
    text=Path(path).read_text()
    if needle not in text:
        raise SystemExit(f"{path}: missing required release marker: {needle}")


def main() -> None:
    project=tomllib.loads(Path("pyproject.toml").read_text())["project"]
    if project["name"] != EXPECTED_NAME:
        raise SystemExit(f"project name mismatch: {project['name']}")
    if project["version"] != EXPECTED_VERSION:
        raise SystemExit(f"project version mismatch: {project['version']}")
    if project["requires-python"] != ">=3.11":
        raise SystemExit(f"unexpected Requires-Python: {project['requires-python']}")

    init_text=Path("src/kavi_capability_compiler/__init__.py").read_text()
    match=re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']',init_text,re.MULTILINE)
    if not match or match.group(1) != EXPECTED_VERSION:
        raise SystemExit("package __version__ does not match release version")

    require("CHANGELOG.md","## 0.1.0")
    require("docs/RELEASE_NOTES_V0.1.md","# KAVI Capability Compiler v0.1.0")
    require("docs/RELEASE_CHECKLIST.md","# v0.1 Release Checklist")

    distribution=Path("docs/DISTRIBUTION_V0.1.md").read_text()
    valid_distribution_markers=(
        "KCC v0.1.0 launches through GitHub Release first.",
        "KCC v0.1.0 is published through GitHub Release.",
    )
    if not any(marker in distribution for marker in valid_distribution_markers):
        raise SystemExit(
            "docs/DISTRIBUTION_V0.1.md: missing GitHub-first distribution marker"
        )

    require("README.md",EXPECTED_DIRECT_WHEEL)
    require("docs/RELEASE_NOTES_V0.1.md",EXPECTED_DIRECT_WHEEL)
    require("SECURITY.md","cryptography>=50.0.1,<51")
    require("SECURITY.md","Remote Streamable HTTP discovery requires HTTPS.")

    result={
        "validation":"kcc.release-metadata.v1",
        "name":EXPECTED_NAME,
        "version":EXPECTED_VERSION,
        "tag":EXPECTED_TAG,
        "requires_python":project["requires-python"],
        "distribution":"github-release-first",
        "pass":True,
    }
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
