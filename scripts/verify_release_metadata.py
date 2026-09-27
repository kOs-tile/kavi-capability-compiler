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
EXPECTED_PAGES_INDEX=(
    "https://kos-tile.github.io/kavi-capability-compiler/simple/"
)


def require(path: str, needle: str) -> None:
    text=Path(path).read_text()
    if needle not in text:
        raise SystemExit(f"{path}: missing required release marker: {needle}")


def forbid_exact_lines(path: str, forbidden: set[str]) -> None:
    lines={line.strip() for line in Path(path).read_text().splitlines()}
    bad=sorted(lines.intersection(forbidden))
    if bad:
        raise SystemExit(
            f"{path}: stale unsupported install command(s): {bad}"
        )


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
    require("README.md",EXPECTED_PAGES_INDEX)
    require("docs/EMBEDDED_SDK.md",EXPECTED_DIRECT_WHEEL)
    require("docs/EMBEDDED_SDK.md",EXPECTED_PAGES_INDEX)

    for extra in ("mcp","signing","all"):
        marker=f'kavi-capability-compiler[{extra}] @ {EXPECTED_DIRECT_WHEEL}'
        require("README.md",marker)
        require("docs/EMBEDDED_SDK.md",marker)

    forbid_exact_lines(
        "docs/EMBEDDED_SDK.md",
        {
            "pip install kavi-capability-compiler",
            'pip install "kavi-capability-compiler[mcp]"',
            'pip install "kavi-capability-compiler[signing]"',
            'pip install "kavi-capability-compiler[all]"',
        },
    )

    require("docs/RELEASE_NOTES_V0.1.md",EXPECTED_DIRECT_WHEEL)
    require("docs/DISTRIBUTION_V0.1.md","The GitHub Pages Simple Repository is live")
    require("docs/RELEASE_NOTES_V0.1.md","The live standards-compliant Simple Repository index")
    require("docs/M5_EXIT.md","**Historical checkpoint.**")
    require("SECURITY.md","cryptography>=50.0.1,<51")
    require("SECURITY.md","Remote Streamable HTTP discovery requires HTTPS.")

    result={
        "validation":"kcc.release-metadata.v1",
        "name":EXPECTED_NAME,
        "version":EXPECTED_VERSION,
        "tag":EXPECTED_TAG,
        "requires_python":project["requires-python"],
        "distribution":"github-release-first",
        "public_install_docs":"verified",
        "pass":True,
    }
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
