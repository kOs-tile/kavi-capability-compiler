"""Offline regression tests for signed scripted-host dispatcher evidence."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmark"))
from synthetic_host_proof import (
    InvalidTrace, InMemoryHost, SCENARIOS, run_trial,
    verify_host_trace, run_campaign, sign_host_trace,
)

KEY = b"synthetic-tests-only-HMAC-key-not-secret-public-0001"

class SyntheticHostEvidenceTests(unittest.TestCase):
    def test_three_blocked_scenarios(self):
        for scenario in ("A01", "A05", "A06"):
            with self.subTest(scenario=scenario):
                b = run_trial(scenario, 0, KEY)
                t = verify_host_trace(b, KEY, expected_scenario=scenario,
                                      expected_trial_id=f"{scenario}-000")
                self.assertEqual(t["actual_dispatch_count"], 0)
                self.assertEqual(t["observed_disallowed_dispatches"], 0)
                self.assertEqual(t["outcome"], "blocked")

    def test_authorized_control_reaches_dispatcher_once(self):
        b = run_trial("CONTROL", 0, KEY)
        t = verify_host_trace(b, KEY, expected_scenario="CONTROL",
                              expected_trial_id="CONTROL-000")
        self.assertEqual(t["actual_dispatch_count"], 1)

    def test_complete_campaign_uses_attested_trial_results(self):
        report = run_campaign(signing_key=KEY, repeat=10)
        self.assertEqual(report["scenario_count"], 4)
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                r = report["scenario_results"][scenario]
                self.assertEqual(r["host_attestations_verified"], 10)
                if scenario == "CONTROL":
                    self.assertIsNone(r["score"])
                else:
                    self.assertEqual(r["score"]["harm_observed"], 0)
                    self.assertFalse(r["score"]["vulnerability_verified"])
                    self.assertFalse(r["score"]["research_gate_passed"])
                self.assertTrue(r["host_dispatch_invariant_passed"])
                self.assertEqual(r["host_policy_decision_mismatches"], 0)
        self.assertEqual(report["scenario_results"]["CONTROL"]["actual_dispatch_count"], 10)

    def test_trace_tamper_detected(self):
        b = run_trial("CONTROL", 0, KEY)
        b["trace"]["events"][2]["capability"] = "delete_record"
        with self.assertRaises(InvalidTrace):
            verify_host_trace(b, KEY, expected_scenario="CONTROL",
                              expected_trial_id="CONTROL-000")

    def test_recompute_digest_without_key_fails(self):
        b = run_trial("CONTROL", 0, KEY)
        b["attestation"]["trace_sha256"] = "0" * 64
        with self.assertRaises(InvalidTrace):
            verify_host_trace(b, KEY, expected_scenario="CONTROL",
                              expected_trial_id="CONTROL-000")

    def test_wrong_hmac_key(self):
        b = run_trial("A01", 0, KEY)
        with self.assertRaisesRegex(InvalidTrace, "HMAC mismatch"):
            verify_host_trace(b, b"some-other-host-key-of-a-different-run-0000001",
                              expected_scenario="A01", expected_trial_id="A01-000")

    def test_cross_trial_replay(self):
        b = run_trial("A01", 0, KEY)
        with self.assertRaisesRegex(InvalidTrace, "identity mismatch"):
            verify_host_trace(b, KEY, expected_scenario="A01",
                              expected_trial_id="A01-001")

    def test_cross_scenario_replay(self):
        b = run_trial("A01", 0, KEY)
        with self.assertRaisesRegex(InvalidTrace, "identity mismatch"):
            verify_host_trace(b, KEY, expected_scenario="A05",
                              expected_trial_id="A01-000")

    def test_unsupported_event_fails(self):
        b = run_trial("A01", 0, KEY)
        b["trace"]["events"].append({"seq": 2, "kind": "fake",
                                      "capability": "delete_record",
                                      "tenant": "tenant_a"})
        with self.assertRaises(InvalidTrace):
            verify_host_trace(b, KEY, expected_scenario="A01",
                              expected_trial_id="A01-000")

    def test_vulnerable_synthetic_host_is_recorded_as_harm(self):
        # Simulated host bug, not an OpenAI or KCC vulnerability.
        b = run_trial("A01", 0, KEY)
        b["trace"]["events"][1]["kind"] = "allow"
        b["trace"]["events"].append({"seq": 2, "kind": "dispatch",
                                      "capability": "delete_record", "tenant": "tenant_a"})
        b = sign_host_trace(b["trace"], KEY)
        t = verify_host_trace(b, KEY, expected_scenario="A01", expected_trial_id="A01-000")
        self.assertEqual(t["observed_disallowed_dispatches"], 1)
        self.assertEqual(t["outcome"], "harm_observed")
        self.assertTrue(t["policy_decision_mismatch"])

    def test_bad_approval_dispatch_is_recorded_as_harm(self):
        b = run_trial("A06", 0, KEY)
        b["trace"]["events"].append({"seq": 2, "kind": "dispatch",
                                      "capability": "send_message", "tenant": "tenant_a"})
        b = sign_host_trace(b["trace"], KEY)
        t = verify_host_trace(b, KEY, expected_scenario="A06", expected_trial_id="A06-000")
        self.assertEqual(t["observed_disallowed_dispatches"], 1)
        self.assertFalse(t["policy_decision_mismatch"])

    def test_dispatcher_is_observed_directly(self):
        host = InMemoryHost("x", [])
        host.dispatch("read_record", "tenant_a")
        self.assertEqual(host.events[0]["kind"], "dispatch")

if __name__ == "__main__":
    unittest.main()
