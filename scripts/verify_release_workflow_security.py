from __future__ import annotations

import re
import sys
from pathlib import Path

CHECKOUT_SHA="d23441a48e516b6c34aea4fa41551a30e30af803"
SETUP_PYTHON_SHA="ece7cb06caefa5fff74198d8649806c4678c61a1"
UPLOAD_ARTIFACT_SHA="ea165f8d65b6e75b540449e92b4886f43607fa02"
DOWNLOAD_ARTIFACT_SHA="634f93cb2916e3fdff6788551b99b062d0335ce0"
PYPI_PUBLISH_SHA="dc37677b2e1c63e2034f94d8a5b11f265b73ba33"

REQUIRED=(
    f"actions/checkout@{CHECKOUT_SHA}",
    f"actions/setup-python@{SETUP_PYTHON_SHA}",
    f"actions/upload-artifact@{UPLOAD_ARTIFACT_SHA}",
    f"actions/download-artifact@{DOWNLOAD_ARTIFACT_SHA}",
    f"pypa/gh-action-pypi-publish@{PYPI_PUBLISH_SHA}",
    "environment:",
    "name: pypi",
    "id-token: write",
    "contents: write",
    "persist-credentials: false",
    "verify_release_metadata.py",
    "verify_reproducible_builds.py",
    "verify_pypi_name_available.py",
    "RELEASE_TARGET_SHA",
    "sha256sum -c",
    "kavi-capability-compiler==0.1.0",
)

FORBIDDEN=(
    "PYPI_API_TOKEN",
    "password:",
    "twine upload",
    "skip-existing: true",
    "skip_existing: true",
)


def main() -> None:
    path=Path(sys.argv[1]) if len(sys.argv)>1 else Path(".github/workflows/release.yml")
    text=path.read_text()
    lowered=text.lower()

    for marker in REQUIRED:
        if marker not in text:
            raise SystemExit(f"{path}: missing release security marker: {marker}")
    for marker in FORBIDDEN:
        if marker.lower() in lowered:
            raise SystemExit(f"{path}: forbidden publication pattern: {marker}")

    if not re.search(r"(?m)^permissions:\s*\n\s+contents:\s*read\s*$",text):
        raise SystemExit(f"{path}: top-level contents: read permission is required")

    publish_match=re.search(
        r"(?ms)^  publish-pypi:.*?^  verify-pypi:",
        text,
    )
    if not publish_match:
        raise SystemExit(f"{path}: publish-pypi job boundary missing")
    publish=publish_match.group(0)
    if "id-token: write" not in publish or "contents: read" not in publish:
        raise SystemExit(f"{path}: PyPI job must have id-token write and contents read")
    if "contents: write" in publish:
        raise SystemExit(f"{path}: PyPI job must not have repository write permission")

    release_match=re.search(
        r"(?ms)^  github-release:.*\Z",
        text,
    )
    if not release_match:
        raise SystemExit(f"{path}: github-release job boundary missing")
    release=release_match.group(0)
    if "contents: write" not in release:
        raise SystemExit(f"{path}: GitHub Release job needs contents write")
    if "id-token: write" in release:
        raise SystemExit(f"{path}: GitHub Release job must not have OIDC write")

    if text.count("environment:\n      name: pypi") < 2:
        raise SystemExit(f"{path}: both privileged publication jobs must use protected pypi environment")

    print("KCC_RELEASE_WORKFLOW_SECURITY: PASS")


if __name__=="__main__":
    main()
