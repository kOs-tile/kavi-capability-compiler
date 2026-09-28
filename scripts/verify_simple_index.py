from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from release_version import release_metadata


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            self.links.append(dict(attrs))


def parse(path: Path) -> Links:
    parser=Links()
    parser.feed(path.read_text())
    return parser


def main() -> None:
    metadata=release_metadata()
    site=Path(sys.argv[1]) if len(sys.argv)>1 else Path("site")
    root=site/"simple"/"index.html"
    detail=site/"simple"/"kavi-capability-compiler"/"index.html"
    if not root.is_file() or not detail.is_file():
        raise SystemExit("simple index pages missing")
    if parse(root).links != [{"href":"./kavi-capability-compiler/"}]:
        raise SystemExit("unexpected simple root links")

    links=parse(detail).links
    if len(links)!=2:
        raise SystemExit(f"expected two distribution links, found {len(links)}")
    filenames=[]
    release_path=f"/releases/download/{metadata['tag']}/"
    for attrs in links:
        href=attrs.get("href","")
        parsed=urlparse(href)
        if parsed.scheme!="https" or parsed.netloc!="github.com":
            raise SystemExit(f"distribution link is not GitHub HTTPS: {href}")
        if release_path not in parsed.path:
            raise SystemExit(f"distribution link is not current versioned release asset: {href}")
        if not re.fullmatch(r"sha256=[0-9a-f]{64}",parsed.fragment):
            raise SystemExit(f"distribution link lacks sha256 fragment: {href}")
        if attrs.get("data-requires-python")!=">=3.11":
            raise SystemExit(f"missing Requires-Python marker: {href}")
        filenames.append(Path(parsed.path).name)

    if filenames.count(metadata["wheel"])!=1:
        raise SystemExit("simple index must expose exact current wheel")
    if filenames.count(metadata["sdist"])!=1:
        raise SystemExit("simple index must expose exact current sdist")
    print("KCC_SIMPLE_INDEX: PASS")


if __name__=="__main__":
    main()
