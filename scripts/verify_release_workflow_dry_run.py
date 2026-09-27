from __future__ import annotations

import re
import sys
from pathlib import Path

FORBIDDEN=(
    "id-token: write",
    "contents: write",
    "pypa/gh-action-pypi-publish",
    "twine upload",
    "gh release create",
    "git tag",
    "git push",
    "PYPI_API_TOKEN",
)


def main() -> None:
    path=Path(sys.argv[1]) if len(sys.argv)>1 else Path(".github/workflows/release.yml")
    text=path.read_text()
    lowered=text.lower()
    for marker in FORBIDDEN:
        if marker.lower() in lowered:
            raise SystemExit(f"{path}: publishing primitive forbidden in dry-run workflow: {marker}")
    if "workflow_dispatch:" not in text:
        raise SystemExit(f"{path}: workflow_dispatch trigger is required")
    if not re.search(r"(?m)^permissions:\s*\n\s+contents:\s*read\s*$",text):
        raise SystemExit(f"{path}: top-level contents: read permission is required")
    if "persist-credentials: false" not in text:
        raise SystemExit(f"{path}: checkout credentials must not persist")
    if "verify_release_metadata.py" not in text:
        raise SystemExit(f"{path}: release metadata verification is required")
    if "verify_reproducible_builds.py" not in text:
        raise SystemExit(f"{path}: reproducibility verification is required")
    print("KCC_RELEASE_WORKFLOW_DRY_RUN: PASS")


if __name__=="__main__":
    main()
