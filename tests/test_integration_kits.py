import ast
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT=Path(__file__).parents[1]
KIT_DIR=ROOT/"examples"/"integration_kits"
KITS=[
    ("openai_tools.py","KCC_KIT_OPENAI: PASS"),
    ("anthropic_tools.py","KCC_KIT_ANTHROPIC: PASS"),
    ("mcp_tools.py","KCC_KIT_MCP: PASS"),
    ("openapi_agent.py","KCC_KIT_OPENAPI: PASS"),
    ("custom_python_agent.py","KCC_KIT_CUSTOM_PYTHON: PASS"),
]
FORBIDDEN={"openai","anthropic","mcp","langgraph"}


def test_integration_kits_execute_and_block_outside_capsule_dispatch():
    for filename,marker in KITS:
        proc=subprocess.run(
            [sys.executable,str(KIT_DIR/filename)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        assert proc.returncode==0, f"{filename}\n{proc.stdout}\n{proc.stderr}"
        assert marker in proc.stdout


def test_integration_kits_do_not_import_vendor_agent_sdks():
    for filename,_ in KITS:
        tree=ast.parse((KIT_DIR/filename).read_text())
        imports=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node,ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        assert not (imports & FORBIDDEN), (filename,imports & FORBIDDEN)


def test_integration_kits_bind_guard_to_current_inventory():
    for filename,_ in KITS:
        source=(KIT_DIR/filename).read_text()
        assert "Guard.from_capsule(capsule,inventory=inventory)" in source


def test_core_dependency_surface_stays_empty():
    data=tomllib.loads((ROOT/"pyproject.toml").read_text())
    assert data["project"]["dependencies"]==[]
