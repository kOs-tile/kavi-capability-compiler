"""Real KCC Guard + synthetic host regression, no model or network."""
from examples.trajectory.kcc_safety_cases import run_once, run_campaign

def test_one_real_guard_run():
    report = run_once(0)
    assert report["synthetic_only"] is True
    assert report["attestation_valid"] is True
    assert report["allowed_dispatches"] == 1
    assert report["forbidden_dispatches"] == 0
    assert set(report["reasons"]) == {"A01", "A05", "A06"}
    assert report["event_count"] == 4

def test_ten_real_guard_runs():
    report = run_campaign(10)
    assert report["actual_openai_testing"] is False
    assert report["signed_host_traces_verified"] == 10
    assert report["allowed_control_dispatches"] == 10
    assert report["forbidden_dispatches"] == 0
    assert report["A01_A05_A06_guard_denials"] == 30
    assert len(report["trace_digests"]) == 10
