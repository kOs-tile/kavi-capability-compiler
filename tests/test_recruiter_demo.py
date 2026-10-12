"""Demo regression: terminal success requires dispatcher-level evidence."""

import json
import subprocess
import sys


def test_five_minute_recruiter_demo():
    process = subprocess.run(
        [sys.executable, "examples/recruiter_demo.py"],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert process.returncode == 0, process.stderr + process.stdout
    assert "KCC_5_MIN_DEMO: PASS" in process.stdout
    evidence_line = next(
        line for line in process.stdout.splitlines() if line.startswith("EVIDENCE_JSON=")
    )
    report = json.loads(evidence_line.removeprefix("EVIDENCE_JSON="))
    assert report["status"] == "PASS"
    assert report["cases"] == 6
    assert report["allowed_dispatches"] == 1
    assert report["denied_dispatches"] == 0
    assert report["delete_dispatches"] == 0
    assert report["denial_reasons"] == {
        "ungranted_deletion": "capability_not_granted",
        "wrong_customer": "parameter_mismatch:customer_id",
        "extra_argument": "parameter_not_granted:export",
        "expired_capsule": "expired",
        "approval_required": "approval_required",
    }
    assert report["synthetic_data_only"] is True
