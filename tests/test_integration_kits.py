import subprocess
import sys

import pytest


KITS=[
    ("generic_python.py","KCC_INTEGRATION_KIT: generic-python: PASS"),
    ("openai_tools.py","KCC_INTEGRATION_KIT: openai-tools: PASS"),
    ("anthropic_tools.py","KCC_INTEGRATION_KIT: anthropic-tools: PASS"),
    ("mcp_tools.py","KCC_INTEGRATION_KIT: mcp-tools: PASS"),
    ("openapi_agent.py","KCC_INTEGRATION_KIT: openapi-agent: PASS"),
]


@pytest.mark.parametrize(("filename","marker"),KITS)
def test_integration_kit_executes(filename,marker):
    proc=subprocess.run(
        [sys.executable,f"examples/integrations/{filename}"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert proc.returncode==0, proc.stderr
    assert marker in proc.stdout
