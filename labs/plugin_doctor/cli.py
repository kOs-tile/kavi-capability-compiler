from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from .ingest import (
    audit_github_package,
    audit_remote_mcp,
    load_local_plugin_files,
)
from .package_validator import validate_package
from .plugin_doctor import audit_source
from .scorecard import write_scorecard


def _emit(value: Any, html_out: str | None = None) -> None:
    if html_out:
        write_scorecard(value, html_out)
    print(json.dumps(value, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(prog="plugin-doctor", allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)

    package = sub.add_parser("package", help="Audit a local portable plugin package")
    package.add_argument("path")
    package.add_argument("--local-only", action="store_true", help="Do not enforce public-submission URL requirements")
    package.add_argument("--html-out")

    github = sub.add_parser("github", help="Audit a GitHub plugin repository")
    github.add_argument("url")
    github.add_argument("--ref")
    github.add_argument("--local-only", action="store_true")
    github.add_argument("--html-out")

    mcp = sub.add_parser("mcp", help="Discover and audit a remote MCP endpoint")
    mcp.add_argument("url")
    mcp.add_argument("--server-name")
    mcp.add_argument("--timeout", type=float, default=30.0)
    mcp.add_argument("--html-out")

    source = sub.add_parser("source", help="Audit a supported tool-definition JSON file")
    source.add_argument("path")
    source.add_argument("--format", required=True, choices=("generic", "mcp", "openai", "anthropic", "openapi"))
    source.add_argument("--namespace", required=True)
    source.add_argument("--server")
    source.add_argument("--html-out")

    args = parser.parse_args()

    if args.command == "package":
        loaded = load_local_plugin_files(args.path)
        _emit(
            {
                "source": loaded["source"],
                "package": validate_package(
                    loaded["files"],
                    public_submission=not args.local_only,
                ),
            },
            args.html_out,
        )
        return

    if args.command == "github":
        report = audit_github_package(
            args.url,
            ref=args.ref,
            token=os.environ.get("GITHUB_TOKEN"),
            public_submission=not args.local_only,
        )
        _emit(report, args.html_out)
        return

    if args.command == "mcp":
        report = asyncio.run(
            audit_remote_mcp(
                args.url,
                server_name=args.server_name,
                timeout_seconds=args.timeout,
            )
        )
        _emit(report, args.html_out)
        return

    payload = json.loads(Path(args.path).read_text(encoding="utf-8"))
    report = audit_source(
        args.format,
        payload,
        namespace=args.namespace,
        server=args.server,
    )
    _emit(report, args.html_out)


if __name__ == "__main__":
    main()
