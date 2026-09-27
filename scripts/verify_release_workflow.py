from __future__ import annotations

from pathlib import Path


def main() -> None:
    path=Path(".github/workflows/release.yml")
    text=path.read_text()

    required=[
        "workflow_dispatch:",
        "default: false",
        'environment: pypi',
        "id-token: write",
        "contents: write",
        "persist-credentials: false",
        'test "$KCC_REF" = "refs/heads/main"',
        'test "$KCC_CONFIRM_VERSION" = "v0.1.0"',
        "pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
        "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093",
        "python scripts/verify_reproducible_builds.py",
        "python -m twine check",
        "sha256sum --check SHA256SUMS",
        "gh release create v0.1.0",
    ]
    missing=[item for item in required if item not in text]
    if missing:
        raise SystemExit(f"release workflow missing required controls: {missing}")

    forbidden=[
        "pull_request_target:",
        "secrets.PYPI",
        "PYPI_TOKEN",
        "password:",
        "username: __token__",
        "skip-existing: true",
    ]
    found=[item for item in forbidden if item in text]
    if found:
        raise SystemExit(f"release workflow contains forbidden controls: {found}")

    if text.count("id-token: write") != 1:
        raise SystemExit("release workflow must grant id-token:write to exactly one job")
    if text.count("environment: pypi") != 1:
        raise SystemExit("release workflow must use exactly one pypi environment gate")

    print("KCC_RELEASE_WORKFLOW_SECURITY: PASS")


if __name__=="__main__":
    main()
