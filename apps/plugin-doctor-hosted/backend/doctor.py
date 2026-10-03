from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from kavi_capability_compiler.core import audit_inventory

REPORT_VERSION = "plugin-doctor.hosted-report.v0"

OPENAI_PLUGIN_GUIDELINES = "https://developers.openai.com/plugins/plugin-guidelines"
OPENAI_PLUGIN_REVIEW = "https://developers.openai.com/plugins/deploy/app-review"
OPENAI_PACKAGE_DOCS = "https://developers.openai.com/plugins/build/plugins"
OPENAI_SKILLS_DOCS = "https://developers.openai.com/plugins/build/skills"
OPENAI_SUBMISSION_ERRORS = "https://developers.openai.com/plugins/deploy/submission-errors"
OPENAI_SUBMISSION_DOCS = "https://developers.openai.com/plugins/deploy/submission"

PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"

_DEDUCTIONS = {"critical": 35, "high": 15, "medium": 6, "low": 2}
_PORTABLE_NAME_RE = re.compile(r"^(?!.*(?:--|\\.\\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
_OPENAI_SUBMISSION_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:[-+][0-9A-Za-z.-]+)?$")


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str
    blocker: bool = False
    remediation: str | None = None
    source_url: str | None = None
    capability: str | None = None
    path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "blocker": self.blocker,
            "remediation": self.remediation,
            "source_url": self.source_url,
            "capability": self.capability,
            "path": self.path,
        }


def _finalize(findings: list[Finding], summary: Mapping[str, Any]) -> dict[str, Any]:
    rows = [finding.as_dict() for finding in findings]
    score = max(0, 100 - sum(_DEDUCTIONS.get(row["severity"], 6) for row in rows))
    blocked = any(row["blocker"] for row in rows)
    return {
        "version": REPORT_VERSION,
        "state": "BLOCKED" if blocked else ("FIX" if rows else "SHIP"),
        "score": score,
        "summary": {**dict(summary), "findings": len(rows), "blockers": sum(1 for row in rows if row["blocker"])},
        "findings": rows,
        "disclaimer": "Plugin Doctor V0 is a deterministic readiness audit. It does not guarantee OpenAI approval, placement, distribution, or security.",
    }


def _parse_json(files: Mapping[str, str], path: str, findings: list[Finding]) -> Any:
    raw = files.get(path)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        findings.append(
            Finding(
                "PD-PKG-JSON",
                "high",
                f"{path} is not valid JSON.",
                True,
                "Replace it with valid UTF-8 JSON.",
                OPENAI_SUBMISSION_ERRORS,
                path=path,
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

def validate_package(files: Mapping[str, str]) -> dict[str, Any]:
    normalized = {str(path).replace("\\", "/"): str(content) for path, content in files.items()}
    findings: list[Finding] = []
    valid_skills = 0
    remote_mcp_servers = 0

    plugin = _parse_json(normalized, "plugin.json", findings)
    if "plugin.json" not in normalized:
        findings.append(Finding("PD-PKG-001", "high", "Portable plugin root is missing plugin.json.", True, "Add root plugin.json using the Agent Plugins schema.", OPENAI_PACKAGE_DOCS, path="plugin.json"))
    elif isinstance(plugin, dict):
        if plugin.get("$schema") != PLUGIN_SCHEMA:
            findings.append(Finding("PD-PKG-003", "high", "plugin.json does not declare the Agent Plugins schema.", True, f'Set "$schema" to "{PLUGIN_SCHEMA}".', OPENAI_PACKAGE_DOCS, path="plugin.json"))
        name = plugin.get("name")
        if not isinstance(name, str) or not name or len(name) > 64 or not _PORTABLE_NAME_RE.fullmatch(name):
            findings.append(Finding("PD-PKG-004", "high", "Plugin name does not conform to the Agent Plugins 1.0 manifest schema.", True, "Use 1-64 lowercase letters/numbers/dots/single hyphens; do not use consecutive '--' or '..'.", PLUGIN_SCHEMA, path="plugin.json"))
        elif not _OPENAI_SUBMISSION_NAME_RE.fullmatch(name):
            findings.append(Finding("PD-OAI-PKG-004", "high", "Plugin name is portable but does not meet OpenAI directory submission naming rules.", True, "For OpenAI directory submission, use lowercase letters/numbers separated by single hyphens.", OPENAI_SUBMISSION_DOCS, path="plugin.json"))

        description = plugin.get("description")
        if description is not None and not isinstance(description, str):
            findings.append(Finding("PD-PKG-005A", "high", "Plugin description must be a string when present.", True, "Use a string value for description.", PLUGIN_SCHEMA, path="plugin.json"))
        elif not isinstance(description, str) or not description.strip():
            findings.append(Finding("PD-PKG-005", "high", "OpenAI directory submission requires a nonempty plugin description.", True, "Add a concise, accurate root description.", OPENAI_SUBMISSION_ERRORS, path="plugin.json"))

        version = plugin.get("version")
        if version is not None and not isinstance(version, str):
            findings.append(Finding("PD-PKG-006A", "high", "Plugin version must be a string when present.", True, "Use a string version or omit it for portable-only packages.", PLUGIN_SCHEMA, path="plugin.json"))
        elif not isinstance(version, str) or not _SEMVER_RE.fullmatch(version):
            findings.append(Finding("PD-OAI-PKG-006", "high", "OpenAI directory submission requires an explicit semantic version.", True, "Add a semantic version such as 0.1.0.", OPENAI_SUBMISSION_ERRORS, path="plugin.json"))

        author = plugin.get("author")
        author_name = author.get("name") if isinstance(author, dict) else None
        if not isinstance(author_name, str) or not author_name.strip():
            findings.append(Finding("PD-OAI-PKG-008", "high", "OpenAI directory submission requires author.name.", True, "Add a nonempty author.name to plugin.json.", OPENAI_SUBMISSION_ERRORS, path="plugin.json"))

    if "mcp.json" in normalized:
        mcp = _parse_json(normalized, "mcp.json", findings)
        if isinstance(mcp, dict):
            if mcp.get("$schema") != MCP_SCHEMA:
                findings.append(Finding("PD-MCP-002", "high", "mcp.json does not declare the Agent Plugins MCP schema.", True, f'Set "$schema" to "{MCP_SCHEMA}".', OPENAI_PACKAGE_DOCS, path="mcp.json"))
            servers = mcp.get("mcpServers")
            if not isinstance(servers, dict):
                findings.append(Finding("PD-MCP-003", "high", "mcp.json must contain an mcpServers object.", True, "Declare named MCP servers under mcpServers.", OPENAI_SUBMISSION_ERRORS, path="mcp.json"))
            else:
                for server_name, server in servers.items():
                    if not isinstance(server_name, str) or not server_name.strip() or not isinstance(server, dict):
                        findings.append(Finding("PD-MCP-004", "high", "Every MCP server needs a nonempty name and object declaration.", True, source_url=OPENAI_SUBMISSION_ERRORS, path="mcp.json"))
                        continue
                    transport = server.get("type")
                    url = server.get("url")
                    if not isinstance(transport, str) or not transport:
                        findings.append(Finding("PD-MCP-005", "high", f"MCP server {server_name!r} is missing its portable transport type.", True, "Declare the portable transport type.", OPENAI_PACKAGE_DOCS, path="mcp.json"))
                    if url is None:
                        findings.append(Finding("PD-MCP-007", "high", f"MCP server {server_name!r} has no remote URL for public submission.", True, "Expose the review server through a public HTTPS endpoint.", OPENAI_SUBMISSION_DOCS, path="mcp.json"))
                    elif isinstance(url, str) and url.startswith("https://"):
                        remote_mcp_servers += 1
                    else:
                        findings.append(Finding("PD-MCP-006", "high", f"MCP server {server_name!r} is not configured with a public HTTPS endpoint.", True, "Use a public HTTPS MCP URL.", OPENAI_SUBMISSION_DOCS, path="mcp.json"))

    skill_paths = [path for path in normalized if path.startswith("skills/")]
    skill_dirs = sorted({path.split("/")[1] for path in skill_paths if len(path.split("/")) >= 2 and path.split("/")[1]})

    for directory in skill_dirs:
        expected = f"skills/{directory}/SKILL.md"
        if directory.startswith("."):
            findings.append(Finding("PD-SKILL-001", "high", "Skill directory names must not be hidden.", True, source_url=OPENAI_SUBMISSION_ERRORS, path=f"skills/{directory}"))
        if expected not in normalized:
            findings.append(Finding("PD-SKILL-002", "high", "Skill directory is missing its required SKILL.md.", True, "Add SKILL.md directly inside the skill directory.", OPENAI_SKILLS_DOCS, path=expected))
            continue
        meta, error = _frontmatter(normalized[expected])
        if error:
            findings.append(Finding("PD-SKILL-003", "high", f"SKILL.md front matter is {error}.", True, "Start SKILL.md with closed YAML front matter containing name and description.", OPENAI_SUBMISSION_ERRORS, path=expected))
            continue
        if not (meta or {}).get("name") or not (meta or {}).get("description"):
            findings.append(Finding("PD-SKILL-004", "high", "SKILL.md front matter requires nonempty name and description.", True, "Add both fields.", OPENAI_SKILLS_DOCS, path=expected))
            continue
        valid_skills += 1

    for path in skill_paths:
        if path.endswith("/SKILL.md") and len(path.split("/")) != 3:
            findings.append(Finding("PD-SKILL-005", "high", "SKILL.md must be in an immediate child directory of skills/.", True, "Move it to skills/<skill-name>/SKILL.md.", OPENAI_SUBMISSION_ERRORS, path=path))

    if valid_skills == 0 and remote_mcp_servers == 0:
        findings.append(Finding("PD-PKG-007", "high", "Plugin package has no usable public runtime surface.", True, "Add at least one valid skill or public HTTPS MCP server.", OPENAI_SUBMISSION_ERRORS))

    return _finalize(findings, {"validation_profile": "openai_directory", "files": len(normalized), "valid_skills": valid_skills, "remote_mcp_servers": remote_mcp_servers})


def audit_inventory_readiness(inventory: Mapping[str, Any]) -> dict[str, Any]:
    findings: list[Finding] = []
    kcc_audit = audit_inventory(dict(inventory))

    for row in kcc_audit.get("findings", []):
        code = row.get("code")
        findings.append(
            Finding(
                str(code or "KCC"),
                str(row.get("severity") or "medium"),
                str(row.get("message") or "KCC authority finding"),
                code == "KCC-A100",
                "Resolve the underlying authority ambiguity before shipping." if code == "KCC-A100" else None,
                capability=row.get("capability"),
            )
        )

    for capability in inventory.get("capabilities", []):
        cid = capability.get("id")
        description = str(capability.get("description") or "").strip()
        schema = capability.get("input_schema") or {}
        effect = capability.get("effect")
        analysis = capability.get("analysis") or {}
        flags = set(analysis.get("risk_flags") or [])
        annotations = capability.get("annotations") or {}

        if not description:
            findings.append(Finding("PD-OAI-D001", "high", "Tool has no model-facing description.", True, "Add an accurate description covering purpose, behavior, limitations, and side effects.", OPENAI_PLUGIN_GUIDELINES, cid))
        elif len(description) < 24:
            findings.append(Finding("PD-D002", "medium", "Tool description is unusually thin for reliable model selection.", False, "Describe when the tool should be used and its important boundaries.", capability=cid))

        missing = [key for key in ("readOnlyHint", "destructiveHint", "openWorldHint") if key not in annotations or not isinstance(annotations.get(key), bool)]
        if missing:
            findings.append(Finding("PD-OAI-A001", "high", "Tool is missing explicit boolean review annotations: " + ", ".join(missing), True, "Set readOnlyHint, destructiveHint, and openWorldHint explicitly.", OPENAI_PLUGIN_GUIDELINES, cid))

        if not schema:
            findings.append(Finding("PD-Q001", "high", "Tool has no bounded input schema.", True, "Provide an explicit JSON Schema for accepted arguments.", capability=cid))

        if effect == "unknown":
            findings.append(Finding("PD-S001", "high", "Capability authority/effect is unknown.", True, "Clarify action semantics so authority can be classified without guessing.", capability=cid))

        if "annotation_conflict" in flags:
            findings.append(Finding("PD-S002", "high", "Declared annotations conflict with observed tool semantics.", True, "Correct annotations or tool semantics.", OPENAI_PLUGIN_GUIDELINES, cid))

        if effect in {"delete", "execute", "financial", "deploy"}:
            findings.append(Finding("PD-R001", "high", f"High-impact capability detected: {effect}.", False, "Require narrow schemas, explicit user intent, and an approval boundary.", OPENAI_PLUGIN_GUIDELINES, cid))
        elif effect in {"write", "external_message"}:
            findings.append(Finding("PD-R002", "medium", f"Mutating capability detected: {effect}.", False, "Verify the write boundary is explicit and minimally scoped.", OPENAI_PLUGIN_GUIDELINES, cid))

    return _finalize(findings, {"capabilities": len(inventory.get("capabilities", []))})
