from __future__ import annotations

import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WORKFLOWS=ROOT/".github"/"workflows"

SECRET_PATTERNS={
    "private_key":re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token":re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    "pypi_token":re.compile(r"pypi-[A-Za-z0-9_-]{20,}"),
    "openai_key":re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    "aws_access_key":re.compile(r"AKIA[0-9A-Z]{16}"),
}
ACTION_REF=re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)",re.MULTILINE)
IMMUTABLE_ACTION=re.compile(r"^[^@]+@[0-9a-f]{40}$")


def text_files():
    excluded={".git",".venv","build","dist",".pytest_cache","__pycache__"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in excluded for part in path.parts):
            continue
        try:
            yield path,path.read_text(encoding="utf-8")
        except (UnicodeDecodeError,OSError):
            continue


def main():
    failures=[]
    for workflow in sorted(WORKFLOWS.glob("*.y*ml")):
        text=workflow.read_text(encoding="utf-8")
        if "pull_request_target:" in text:
            failures.append(f"{workflow.relative_to(ROOT)}: pull_request_target is not allowed")
        if re.search(r"(?m)^\s*permissions:\s*write-all\s*$",text):
            failures.append(f"{workflow.relative_to(ROOT)}: write-all permissions are not allowed")
        for ref in ACTION_REF.findall(text):
            if ref.startswith("./"):
                continue
            if not IMMUTABLE_ACTION.fullmatch(ref):
                failures.append(f"{workflow.relative_to(ROOT)}: mutable action ref {ref}")

    forbidden_names={".env",".pypirc"}
    forbidden_suffixes={".pem",".key",".p12",".pfx"}
    for path,text in text_files():
        rel=path.relative_to(ROOT)
        if path.name in forbidden_names or path.suffix.lower() in forbidden_suffixes:
            failures.append(f"{rel}: forbidden secret-bearing filename")
        for label,pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                failures.append(f"{rel}: possible {label} material")

    result={"validation":"kcc.release-security-preflight.v1","failures":sorted(set(failures))}
    result["pass"]=not result["failures"]
    print(json.dumps(result,sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__=="__main__":
    main()
