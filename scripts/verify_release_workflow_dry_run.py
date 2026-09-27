from __future__ import annotations

import re
import sys
from pathlib import Path


def section(text: str, start: str, end: str | None = None) -> str:
    left=text.find(start)
    if left < 0:
        raise SystemExit(f"release workflow missing section: {start.strip()}")
    if end is None:
        return text[left:]
    right=text.find(end,left+len(start))
    if right < 0:
        raise SystemExit(f"release workflow missing section: {end.strip()}")
    return text[left:right]


def main() -> None:
    path=Path(sys.argv[1]) if len(sys.argv)>1 else Path(".github/workflows/release.yml")
    text=path.read_text()

    if "pull_request_target:" in text:
        raise SystemExit(f"{path}: pull_request_target is forbidden")
    if "workflow_dispatch:" not in text or "pull_request:" not in text:
        raise SystemExit(f"{path}: PR dry-run plus workflow_dispatch are required")
    if not re.search(r"(?m)^permissions:\s*\n\s+contents:\s*read\s*$",text):
        raise SystemExit(f"{path}: top-level contents: read permission is required")
    if "persist-credentials: false" not in text:
        raise SystemExit(f"{path}: checkout credentials must not persist")
    for marker in ("secrets.PYPI","PYPI_API_TOKEN","twine upload","skip-existing: true"):
        if marker.lower() in text.lower():
            raise SystemExit(f"{path}: forbidden publication pattern: {marker}")

    build=section(text,"  build-release-artifacts:\n","  publish-pypi:\n")
    publish=section(text,"  publish-pypi:\n","  create-github-release:\n")
    release=section(text,"  create-github-release:\n")

    if "id-token: write" in build or "contents: write" in build:
        raise SystemExit(f"{path}: build job must not own publish/write credentials")
    if "actions: read" not in build or "contents: read" not in build:
        raise SystemExit(f"{path}: build job must use explicit read-only permissions")
    for marker in (
        'test "$KCC_REF" = "refs/heads/main"',
        'test "$TARGET_SHA" = "$WORKFLOW_SHA"',
        'test "$KCC_CONFIRM_VERSION" = "v0.1.0"',
        'row.get("name")=="test"',
        'row.get("event")=="push"',
        'row.get("conclusion")=="success"',
        "verify_release_metadata.py",
        "verify_reproducible_builds.py",
        "twine check",
    ):
        if marker not in build:
            raise SystemExit(f"{path}: build/publish preflight missing: {marker}")

    if "environment: pypi" not in publish:
        raise SystemExit(f"{path}: PyPI job must use the protected pypi environment")
    if publish.count("id-token: write") != 1 or "contents: read" not in publish:
        raise SystemExit(f"{path}: PyPI job requires exactly one OIDC grant plus contents:read")
    if "contents: write" in publish:
        raise SystemExit(f"{path}: PyPI job must not have repository write permission")
    if "github.event_name == 'workflow_dispatch' && inputs.publish" not in publish:
        raise SystemExit(f"{path}: PyPI job is not explicitly gated to manual publish")
    if "pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33" not in publish:
        raise SystemExit(f"{path}: pinned PyPA publish action is required")
    if "sha256sum --check SHA256SUMS" not in publish:
        raise SystemExit(f"{path}: PyPI job must reverify artifact checksums")

    if "contents: write" not in release or "id-token: write" in release:
        raise SystemExit(f"{path}: GitHub Release job must own contents:write without OIDC")
    if "github.event_name == 'workflow_dispatch' && inputs.publish" not in release:
        raise SystemExit(f"{path}: GitHub Release job is not explicitly gated to manual publish")
    if "needs:" not in release or "publish-pypi" not in release:
        raise SystemExit(f"{path}: GitHub Release must depend on successful PyPI publication")
    if "gh release create v0.1.0" not in release:
        raise SystemExit(f"{path}: exact v0.1.0 release creation is required")

    if text.count("id-token: write") != 1:
        raise SystemExit(f"{path}: OIDC must be granted to exactly one job")
    if text.count("contents: write") != 1:
        raise SystemExit(f"{path}: repository write permission must exist in exactly one job")

    print("KCC_RELEASE_WORKFLOW_SECURITY: PASS")


if __name__=="__main__":
    main()
