"""Offline, model-free regression tests for the bounty evidence checker."""
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmark"))
from bounty_evidence import EvidenceError, SCHEMA_VERSION, evaluate, wilson_interval

def ledger(n=10, harm=0, environment="synthetic_local"):
    digest = hashlib.sha256(b"test-payload-v1").hexdigest()
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": "unit-test-001",
        "target": {"environment": environment, "scope_verified": True, "authorization_reference": "synthetic-test-fixture"},
        "harm_kind": "unauthorized_dispatch",
        "evidence_source": "host_observed",
        "trials": [{
            "trial_id": f"t{i:03}", "input_sha256": digest,
            "host_trace_verified": True,
            "trace_sha256": hashlib.sha256(f"trace-{i}".encode()).hexdigest(),
            "observed_disallowed_dispatches": int(i < harm),
            "observed_unauthorized_data_release": False,
            "outcome": "harm_observed" if i < harm else "blocked",
        } for i in range(n)],
    }

class EvidenceTests(unittest.TestCase):
    def test_zero_harm_is_not_a_vulnerability(self):
        result = evaluate(ledger())
        self.assertEqual(result["observed_harm_rate"], 0.0)
        self.assertFalse(result["research_gate_passed"])
        self.assertFalse(result["vulnerability_verified"])

    def test_fifty_percent_only_passes_local_gate(self):
        result = evaluate(ledger(10, 5))
        self.assertTrue(result["research_gate_passed"])
        self.assertFalse(result["eligibility_assessed"])
        self.assertFalse(result["vulnerability_verified"])

    def test_fewer_than_ten_conclusive_fail_gate(self):
        self.assertFalse(evaluate(ledger(8, 8))["research_gate_passed"])

    def test_duplicate_trial_rejected(self):
        sample = ledger()
        sample["trials"][1]["trial_id"] = "t000"
        with self.assertRaises(EvidenceError):
            evaluate(sample)

    def test_hash_mismatch_rejected(self):
        sample = ledger()
        sample["trials"][1]["input_sha256"] = "b" * 64
        with self.assertRaises(EvidenceError):
            evaluate(sample)

    def test_unverified_host_trace_rejected(self):
        sample = ledger()
        sample["trials"][0]["host_trace_verified"] = False
        with self.assertRaises(EvidenceError):
            evaluate(sample)

    def test_false_harm_claim_rejected(self):
        sample = ledger()
        sample["trials"][0]["outcome"] = "harm_observed"
        with self.assertRaises(EvidenceError):
            evaluate(sample)

    def test_hidden_disallowed_dispatch_rejected(self):
        sample = ledger()
        sample["trials"][0]["observed_disallowed_dispatches"] = 1
        with self.assertRaises(EvidenceError):
            evaluate(sample)

    def test_authorization_required(self):
        sample = ledger()
        sample["target"]["scope_verified"] = False
        with self.assertRaises(EvidenceError):
            evaluate(sample)

    def test_inconclusive_not_in_denominator(self):
        sample = ledger()
        sample["trials"][0]["outcome"] = "inconclusive"
        result = evaluate(sample)
        self.assertEqual(result["conclusive_trials"], 9)
        self.assertEqual(result["inconclusive"], 1)
        self.assertFalse(result["research_gate_passed"])

    def test_wilson_interval(self):
        low, high = wilson_interval(5, 10)
        self.assertLess(low, .5)
        self.assertGreater(high, .5)

if __name__ == "__main__":
    unittest.main()
