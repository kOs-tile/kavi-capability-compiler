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


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(prog="plugin-doctor", allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)

    package = sub.add_parser("package", help="Audit a local portable plugin package")
    package.add_argument("path")
    package.add_argument("--local-only", action="store_true", help="Do not enforce public-submission URL requirements")

    github = sub.add_parser("github", help="Audit a GitHub plugin repository")
    github.add_argument("url")
    github.add_argument("--ref")
    github.add_argument("--local-only", action="store_true")

    mcp = sub.add_parser("mcp", help="Discover and audit a remote MCP endpoint")
    mcp.add_argument("url")
    mcp.add_argument("--server-name")
    mcp.add_argument("--timeout", type=float, default=30.0)

    source = sub.add_parser("source", help="Audit a supported tool-definition JSON file")
    source.add_argument("path")
    source.add_argument("--format", required=True, choices=("generic", "mcp", "openai", "anthropic", "openapi"))
    source.add_argument("--namespace", required=True)
    source.add_argument("--server")

    args = parser.parse_args()

    if args.command == "package":
        loaded = load_local_plugin_files(args.path)
        _print(
            {
                "source": loaded["source"],
                "package": validate_package(
                    loaded["files"],
                    public_submission=not args.local_only,
                ),
            }
        )
        return

    if args.command == "github":
        _print(
            audit_github_package(
                args.url,
                ref=args.ref,
                token=os.environ.get("GITHUB_TOKEN"),
                public_submission=not args.local_only,
            )
        )
        return

    if args.command == "mcp":
        _print(
            asyncio.run(
                audit_remote_mcp(
                    args.url,
                    server_name=args.server_name,
                    timeout_seconds=args.timeout,
                )
            )
        )
        return

    payload = json.loads(Path(args.path).read_text(encoding="utf-8"))
    _print(
        audit_source(
            args.format,
            payload,
            namespace=args.namespace,
            server=args.server,
        )
    )


if __name__ == "__main__":
    main()
