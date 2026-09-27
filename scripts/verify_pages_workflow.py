from __future__ import annotations

import re
import sys
from pathlib import Path


def main(path: str | Path | None = None) -> None:
    path=Path(path) if path is not None else Path(sys.argv[1] if len(sys.argv)>1 else ".github/workflows/pages.yml")
    text=path.read_text()
    if "pull_request" in text or "push:" in text:
        raise SystemExit("Pages index deployment must be manual-only")
    if re.search(r"v0\.1\.\d+",text):
        raise SystemExit("Pages workflow must derive the patch tag instead of hardcoding v0.1.x")
    for marker in (
        "workflow_dispatch:",
        "contents: read",
        "pages: write",
        "id-token: write",
        "environment:",
        "name: github-pages",
        "scripts/release_version.py version",
        "scripts/release_version.py tag",
        'gh release download "$KCC_TAG"',
        'release.get("immutable") is not True',
        "sha256sum --check SHA256SUMS",
        "build_simple_index.py",
        "verify_simple_index.py",
        "actions/configure-pages@983d7736d9b0ae728b81ab479565c72886d7745b",
        "actions/upload-pages-artifact@7b1f4a764d45c48632c6b24a0339c27f5614fb0b",
        "actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e",
    ):
        if marker not in text:
            raise SystemExit(f"Pages workflow missing: {marker}")
    if "contents: write" in text:
        raise SystemExit("Pages workflow must not modify repository contents")
    if text.count("pages: write")!=1 or text.count("id-token: write")!=1:
        raise SystemExit("Pages/OIDC permissions must each appear exactly once")
    print("KCC_PAGES_WORKFLOW: PASS")


if __name__=="__main__":
    main()
