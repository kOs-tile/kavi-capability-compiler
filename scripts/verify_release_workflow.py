from __future__ import annotations

import re
import sys
from pathlib import Path


def section(text: str, start: str, end: str | None = None) -> str:
    left=text.find(start)
    if left<0:
        raise SystemExit(f"missing workflow section: {start.strip()}")
    if end is None:
        return text[left:]
    right=text.find(end,left+len(start))
    if right<0:
        raise SystemExit(f"missing workflow section: {end.strip()}")
    return text[left:right]


def main(path: str | Path | None = None) -> None:
    path=Path(path) if path is not None else Path(sys.argv[1] if len(sys.argv)>1 else ".github/workflows/release.yml")
    text=path.read_text()
    if "pull_request_target:" in text:
        raise SystemExit("pull_request_target is forbidden")
    if "workflow_dispatch:" not in text or "pull_request:" not in text:
        raise SystemExit("release workflow requires PR dry-run plus workflow_dispatch")
    if not re.search(r"(?m)^permissions:\s*\n\s+contents:\s*read\s*$",text):
        raise SystemExit("top-level contents:read is required")
    for marker in ("pypa/gh-action-pypi-publish","id-token: write","PYPI_API_TOKEN","twine upload"):
        if marker.lower() in text.lower():
            raise SystemExit(f"PyPI/publication credential primitive forbidden in GitHub-first workflow: {marker}")

    build=section(text,"  build-release-artifacts:\n","  create-github-release:\n")
    release=section(text,"  create-github-release:\n")
    if "contents: write" in build:
        raise SystemExit("build job must not own repository write permission")
    for marker in (
        "actions: read",
        "contents: read",
        'test "$KCC_REF" = "refs/heads/main"',
        'test "$TARGET_SHA" = "$WORKFLOW_SHA"',
        'test "$KCC_CONFIRM_VERSION" = "v0.1.0"',
        'row.get("name")=="test"',
        'row.get("event")=="push"',
        'row.get("conclusion")=="success"',
        "verify_reproducible_builds.py",
        "twine check",
        "build_simple_index.py",
        "verify_simple_index.py",
    ):
        if marker not in build:
            raise SystemExit(f"release preflight missing: {marker}")

    if "contents: write" not in release:
        raise SystemExit("GitHub release job requires contents:write")
    if "id-token: write" in release or "pages: write" in release:
        raise SystemExit("GitHub release job must not own OIDC or Pages permission")
    if "github.event_name == 'workflow_dispatch' && inputs.publish" not in release:
        raise SystemExit("GitHub release job is not manual-publish gated")
    if "sha256sum --check SHA256SUMS" not in release:
        raise SystemExit("GitHub release job must reverify checksums")
    if "gh release create v0.1.0" not in release:
        raise SystemExit("exact v0.1.0 release creation is required")
    if text.count("contents: write")!=1:
        raise SystemExit("contents:write must exist in exactly one job")
    print("KCC_GITHUB_RELEASE_WORKFLOW: PASS")


if __name__=="__main__":
    main()
