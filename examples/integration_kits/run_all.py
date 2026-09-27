"""Execute every dependency-free KCC integration kit."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
KITS=[
    "openai_tools.py",
    "anthropic_tools.py",
    "mcp_tools.py",
    "openapi_agent.py",
    "custom_python_agent.py",
]
for name in KITS:
    proc=subprocess.run(
        [sys.executable,str(ROOT/name)],
        cwd=ROOT.parents[1],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if proc.returncode != 0:
        raise SystemExit(f"{name} failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    print(proc.stdout.strip())
print("KCC_INTEGRATION_KITS: PASS")
