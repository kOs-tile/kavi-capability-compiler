from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlsplit

PACKAGE_REPORT_VERSION = "plugin-doctor.package-report.v0"
PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"

OPENAI_PACKAGE_DOCS = "https://developers.openai.com/plugins/build/plugins"
OPENAI_SKILLS_DOCS = "https://developers.openai.com/plugins/build/skills"
OPENAI_SUBMISSION_ERRORS = "https://developers.openai.com/plugins/deploy/submission-errors"
OPENAI_SUBMISSION_DOCS = "https://developers.openai.com/plugins/deploy/submission"

_PORTABLE_NAME_RE = re.compile(r"^(?!.*(?:--|\\.\\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
_OPENAI_SUBMISSION_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:[-+][0-9A-Za-z.-]+)?$")

_DEDUCTIONS = {"critical": 35, "high": 15, "medium": 6, "low": 2}


@dataclass(frozen=True)
class PackageFinding:
    code: str
    severity: str
    message: str
    path: str | None = None
    blocker: bool = False
    remediation: str | None = None
    source_url: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
            "blocker": self.blocker,
            "remediation": self.remediation,
            "source_url": self.source_url,
        }


def _score_findings(rows: list[dict[str, Any]]) -> tuple[int, int]:
    """Score rule coverage, not raw repetition count.

    Repeated instances of the same rule remain visible in findings/blockers but
    deduct from the 100-point heuristic only once, avoiding plugin-size bias.
    """
    severities_by_code: dict[str, str] = {}
    rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    for index, row in enumerate(rows):
        code = str(row.get("code") or f"finding-{index}")
        severity = str(row.get("severity") or "medium")
        current = severities_by_code.get(code)
        if current is None or rank.get(severity, 1) > rank.get(current, 1):
            severities_by_code[code] = severity
    score = max(0, 100 - sum(_DEDUCTIONS.get(severity, 6) for severity in severities_by_code.values()))
    return score, len(severities_by_code)


def _parse_json_file(files: Mapping[str, str], path: str, findings: list[PackageFinding]) -> Any:
    raw = files.get(path)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        findings.append(
            PackageFinding(
                code="PD-PKG-JSON",
                severity="high",
                path=path,
                blocker=True,
                message=f"{path} is not valid JSON: {type(exc).__name__}.",
                remediation="Replace it with valid UTF-8 JSON.",
                source_url=OPENAI_SUBMISSION_ERRORS,
            )
        )
        return None


def _frontmatter(text: str) -> tuple[dict[str, str] | None, str | None]:
    """Parse the two Agent Skills identity fields without pretending to be a full YAML loader.

    Supports plain/quoted scalar values and YAML literal/folded block scalars for
    top-level name/description. Nested metadata is ignored.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "missing"
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None, "unclosed"

    data: dict[str, str] = {}
    i = 1
    while i < end:
        raw = lines[i]
        stripped = raw.strip()
        i += 1
        if not stripped or stripped.startswith("#") or raw[:1].isspace():
            continue
        if ":" not in raw:
            return None, "malformed"
        key, value = raw.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            return None, "malformed"

        if value in {"|", "|-", "|+", ">", ">-", ">+"}:
            block: list[str] = []
            while i < end:
                candidate = lines[i]
                if candidate and not candidate[:1].isspace():
                    break
                block.append(candidate.strip())
                i += 1
            sep = "\n" if value.startswith("|") else " "
            data[key] = sep.join(part for part in block if part).strip()
        else:
            data[key] = value.strip('"').strip("'")
    return data, None

def _is_public_https(url: str) -> bool:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or not host:
        return False
    if host == "localhost" or host.endswith(".localhost"):
        return False
    if host in {"127.0.0.1", "::1"}:
        return False
    return True


def validate_package(
    files: Mapping[str, str],
    *,
    public_submission: bool = True,
) -> dict[str, Any]:
    """Validate the portable plugin package surface without executing package code."""

    normalized = {}
    for path, content in files.items():
        normalized_path = str(path).replace("\\", "/")
        if normalized_path.startswith("./"):
            normalized_path = normalized_path[2:]
        normalized[normalized_path] = str(content)
    findings: list[PackageFinding] = []
    valid_skills = 0
    configured_mcp_servers = 0
    remote_mcp_servers = 0

    if "plugin.json" not in normalized:
        findings.append(
            PackageFinding(
                code="PD-PKG-001",
                severity="high",
                path="plugin.json",
                blocker=True,
                message="Portable plugin root is missing plugin.json.",
                remediation="Add root plugin.json using the Agent Plugins schema.",
                source_url=OPENAI_PACKAGE_DOCS,
            )
        )
        plugin = None
    else:
        plugin = _parse_json_file(normalized, "plugin.json", findings)

    if plugin is not None:
        if not isinstance(plugin, dict):
            findings.append(
                PackageFinding(
                    code="PD-PKG-002",
                    severity="high",
                    path="plugin.json",
                    blocker=True,
                    message="plugin.json must contain a JSON object.",
                    remediation="Use the portable plugin manifest object format.",
                    source_url=OPENAI_PACKAGE_DOCS,
                )
            )
        else:
            if plugin.get("$schema") != PLUGIN_SCHEMA:
                findings.append(
                    PackageFinding(
                        code="PD-PKG-003",
                        severity="high",
                        path="plugin.json",
                        blocker=True,
                        message="plugin.json does not declare the portable Agent Plugins schema.",
                        remediation=f'Set "$schema" to "{PLUGIN_SCHEMA}".',
                        source_url=OPENAI_PACKAGE_DOCS,
                    )
                )

            name = plugin.get("name")
            if not isinstance(name, str) or not name or len(name) > 64 or not _PORTABLE_NAME_RE.fullmatch(name):
                findings.append(
                    PackageFinding(
                        code="PD-PKG-004",
                        severity="high",
                        path="plugin.json",
                        blocker=True,
                        message="Plugin name does not conform to the Agent Plugins 1.0 manifest schema.",
                        remediation="Use 1-64 lowercase letters/numbers/dots/single hyphens; do not use consecutive '--' or '..'.",
                        source_url=PLUGIN_SCHEMA,
                    )
                )
            elif public_submission and not _OPENAI_SUBMISSION_NAME_RE.fullmatch(name):
                findings.append(
                    PackageFinding(
                        code="PD-OAI-PKG-004",
                        severity="high",
                        path="plugin.json",
                        blocker=True,
                        message="Plugin name is portable but does not meet OpenAI directory submission naming rules.",
                        remediation="For OpenAI directory submission, use lowercase letters/numbers separated by single hyphens.",
                        source_url=OPENAI_SUBMISSION_DOCS,
                    )
                )

            description = plugin.get("description")
            if description is not None and not isinstance(description, str):
                findings.append(
                    PackageFinding(
                        code="PD-PKG-005A",
                        severity="high",
                        path="plugin.json",
                        blocker=True,
                        message="Plugin description must be a string when present.",
                        remediation="Use a string value for description.",
                        source_url=PLUGIN_SCHEMA,
                    )
                )
            elif public_submission and (not isinstance(description, str) or not description.strip()):
                findings.append(
                    PackageFinding(
                        code="PD-PKG-005",
                        severity="high",
                        path="plugin.json",
                        blocker=True,
                        message="OpenAI directory submission requires a nonempty plugin description.",
                        remediation="Add a concise, accurate root description.",
                        source_url=OPENAI_SUBMISSION_ERRORS,
                    )
                )

            version = plugin.get("version")
            if version is not None and not isinstance(version, str):
                findings.append(
                    PackageFinding(
                        code="PD-PKG-006A",
                        severity="high",
                        path="plugin.json",
                        blocker=True,
                        message="Plugin version must be a string when present.",
                        remediation="Use a string version or omit it for portable-only packages.",
                        source_url=PLUGIN_SCHEMA,
                    )
                )
            elif public_submission and (not isinstance(version, str) or not _SEMVER_RE.fullmatch(version)):
                findings.append(
                    PackageFinding(
                        code="PD-OAI-PKG-006",
                        severity="high",
                        path="plugin.json",
                        blocker=True,
                        message="OpenAI directory submission requires an explicit semantic version.",
                        remediation="Add a semantic version such as 0.1.0.",
                        source_url=OPENAI_SUBMISSION_ERRORS,
                    )
                )

            author = plugin.get("author")
            author_name = author.get("name") if isinstance(author, dict) else None
            if public_submission and (not isinstance(author_name, str) or not author_name.strip()):
                findings.append(
                    PackageFinding(
                        code="PD-OAI-PKG-008",
                        severity="high",
                        path="plugin.json",
                        blocker=True,
                        message="OpenAI directory submission requires author.name.",
                        remediation="Add a nonempty author.name to plugin.json.",
                        source_url=OPENAI_SUBMISSION_ERRORS,
                    )
                )

    if "mcp.json" in normalized:
        mcp = _parse_json_file(normalized, "mcp.json", findings)
        if mcp is not None:
            if not isinstance(mcp, dict):
                findings.append(
                    PackageFinding(
                        code="PD-MCP-001",
                        severity="high",
                        path="mcp.json",
                        blocker=True,
                        message="mcp.json must contain a JSON object.",
                        remediation="Use the portable MCP manifest object format.",
                        source_url=OPENAI_PACKAGE_DOCS,
                    )
                )
            else:
                if mcp.get("$schema") != MCP_SCHEMA:
                    findings.append(
                        PackageFinding(
                            code="PD-MCP-002",
                            severity="high",
                            path="mcp.json",
                            blocker=True,
                            message="mcp.json does not declare the Agent Plugins MCP schema.",
                            remediation=f'Set "$schema" to "{MCP_SCHEMA}".',
                            source_url=OPENAI_PACKAGE_DOCS,
                        )
                    )
                servers = mcp.get("mcpServers")
                if not isinstance(servers, dict):
                    findings.append(
                        PackageFinding(
                            code="PD-MCP-003",
                            severity="high",
                            path="mcp.json",
                            blocker=True,
                            message="mcp.json must contain an mcpServers object.",
                            remediation="Declare named MCP servers under mcpServers.",
                            source_url=OPENAI_SUBMISSION_ERRORS,
                        )
                    )
                else:
                    for server_name, server in servers.items():
                        if not isinstance(server_name, str) or not server_name.strip() or not isinstance(server, dict):
                            findings.append(
                                PackageFinding(
                                    code="PD-MCP-004",
                                    severity="high",
                                    path="mcp.json",
                                    blocker=True,
                                    message="Every MCP server needs a nonempty name and object declaration.",
                                    source_url=OPENAI_SUBMISSION_ERRORS,
                                )
                            )
                            continue
                        configured_mcp_servers += 1
                        transport = server.get("type")
                        url = server.get("url")
                        if not isinstance(transport, str) or not transport:
                            findings.append(
                                PackageFinding(
                                    code="PD-MCP-005",
                                    severity="high",
                                    path="mcp.json",
                                    blocker=True,
                                    message=f"MCP server {server_name!r} is missing its portable transport type.",
                                    remediation="Declare the server transport type in portable mcp.json.",
                                    source_url=OPENAI_PACKAGE_DOCS,
                                )
                            )
                        if public_submission and url is None:
                            findings.append(
                                PackageFinding(
                                    code="PD-MCP-007",
                                    severity="high",
                                    path="mcp.json",
                                    blocker=True,
                                    message=f"MCP server {server_name!r} has no remote URL for public submission.",
                                    remediation="Expose the MCP server through a publicly accessible HTTPS endpoint for review.",
                                    source_url=OPENAI_SUBMISSION_DOCS,
                                )
                            )
                        if url is not None:
                            remote_mcp_servers += 1
                            if public_submission and (not isinstance(url, str) or not _is_public_https(url)):
                                findings.append(
                                    PackageFinding(
                                        code="PD-MCP-006",
                                        severity="high",
                                        path="mcp.json",
                                        blocker=True,
                                        message=f"MCP server {server_name!r} is not configured with a public HTTPS endpoint.",
                                        remediation="Deploy the review server to a publicly accessible HTTPS URL.",
                                        source_url=OPENAI_SUBMISSION_DOCS,
                                    )
                                )

    skill_paths = [path for path in normalized if path.startswith("skills/")]
    skill_dirs = sorted({path.split("/")[1] for path in skill_paths if len(path.split("/")) >= 2 and path.split("/")[1]})

    for directory in skill_dirs:
        if directory.startswith("."):
            findings.append(
                PackageFinding(
                    code="PD-SKILL-001",
                    severity="high",
                    path=f"skills/{directory}",
                    blocker=True,
                    message="Skill directory names must not be hidden.",
                    source_url=OPENAI_SUBMISSION_ERRORS,
                )
            )

        expected = f"skills/{directory}/SKILL.md"
        if expected not in normalized:
            findings.append(
                PackageFinding(
                    code="PD-SKILL-002",
                    severity="high",
                    path=expected,
                    blocker=True,
                    message="Skill directory is missing its required SKILL.md.",
                    remediation="Add SKILL.md directly inside the skill directory.",
                    source_url=OPENAI_SKILLS_DOCS,
                )
            )
            continue

        frontmatter, error = _frontmatter(normalized[expected])
        if error:
            findings.append(
                PackageFinding(
                    code="PD-SKILL-003",
                    severity="high",
                    path=expected,
                    blocker=True,
                    message=f"SKILL.md front matter is {error}.",
                    remediation="Start SKILL.md with closed YAML front matter containing name and description.",
                    source_url=OPENAI_SUBMISSION_ERRORS,
                )
            )
            continue

        name = (frontmatter or {}).get("name", "").strip()
        description = (frontmatter or {}).get("description", "").strip()
        if not name or not description:
            findings.append(
                PackageFinding(
                    code="PD-SKILL-004",
                    severity="high",
                    path=expected,
                    blocker=True,
                    message="SKILL.md front matter requires nonempty name and description.",
                    remediation="Add both fields so the model knows what the skill is and when to consider it.",
                    source_url=OPENAI_SKILLS_DOCS,
                )
            )
            continue
        valid_skills += 1

    usable_mcp_servers = remote_mcp_servers if public_submission else configured_mcp_servers
    if public_submission and valid_skills == 0 and usable_mcp_servers == 0:
        findings.append(
            PackageFinding(
                code="PD-PKG-007",
                severity="high",
                blocker=True,
                message="Plugin package has no usable runtime surface.",
                remediation="Add at least one valid skill or a configured MCP server.",
                source_url=OPENAI_SUBMISSION_ERRORS,
            )
        )

    rows = [finding.as_dict() for finding in findings]
    score, unique_rule_codes = _score_findings(rows)
    blocked = any(row["blocker"] for row in rows)

    return {
        "version": PACKAGE_REPORT_VERSION,
        "state": "BLOCKED" if blocked else ("FIX" if rows else "SHIP"),
        "score": score,
        "summary": {
            "validation_profile": "openai_directory" if public_submission else "agent_plugins_1_0",
            "files": len(normalized),
            "valid_skills": valid_skills,
            "configured_mcp_servers": configured_mcp_servers,
            "remote_mcp_servers": remote_mcp_servers,
            "findings": len(rows),
            "unique_rule_codes": unique_rule_codes,
            "blockers": sum(1 for row in rows if row["blocker"]),
        },
        "findings": rows,
        "disclaimer": "Package validation reflects published structure/review rules plus explicitly labeled KAVI checks; it does not guarantee approval.",
    }
