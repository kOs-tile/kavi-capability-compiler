import json
import subprocess
import sys


def test_adversarial_sdk_benchmark_contract():
    proc=subprocess.run(
        [sys.executable,"benchmark/adversarial_sdk.py"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode==0, proc.stderr
    result=json.loads(proc.stdout)
    assert result["benchmark"]=="kcc.adversarial-sdk.v1"
    assert result["enforced_cases"]>=10
    assert result["all_enforced_cases_pass"]
    assert result["boundaries"]["replay"]["classification"]=="host_responsibility"
    assert result["boundaries"]["replay"]["observed_valid_before_expiry"]
    assert result["boundaries"]["direct_dispatcher_bypass"]["classification"]=="outside_kcc_mediation"
    assert result["boundaries"]["direct_dispatcher_bypass"]["observed_direct_host_call"]
