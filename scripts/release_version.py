from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROJECT_NAME="kavi-capability-compiler"
DIST_NAME="kavi_capability_compiler"
VERSION_RE=re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def project_version() -> str:
    project=tomllib.loads((ROOT/"pyproject.toml").read_text())["project"]
    if project.get("name") != PROJECT_NAME:
        raise ValueError(f"unexpected project name: {project.get('name')}")
    version=str(project.get("version") or "")
    if not VERSION_RE.fullmatch(version):
        raise ValueError(f"unsupported release version: {version!r}")
    return version


def release_metadata() -> dict[str,str]:
    version=project_version()
    return {
        "project":PROJECT_NAME,
        "dist_name":DIST_NAME,
        "version":version,
        "tag":f"v{version}",
        "wheel":f"{DIST_NAME}-{version}-py3-none-any.whl",
        "wheel_glob":f"{DIST_NAME}-{version}-*.whl",
        "sdist":f"{DIST_NAME}-{version}.tar.gz",
        "notes":f"docs/RELEASE_NOTES_V{version}.md",
    }


def main() -> None:
    metadata=release_metadata()
    key=sys.argv[1] if len(sys.argv)>1 else "version"
    if key not in metadata:
        raise SystemExit(f"unknown release metadata key: {key}")
    print(metadata[key])


if __name__=="__main__":
    main()
