"""Offline Responses transport replay with real KCC Guard, never API network.

A simulated HTTP response tests the ingestion contract; this is NOT a model run.
"""
from __future__ import annotations
import json
import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from evals import openai_responses_probe as probe


ROOT = Path(__file__).resolve().parents[1] / "evals"


class TestNoCostReplay(unittest.TestCase):
    def load(self):
        return probe.parse_dataset(json.loads(
            (ROOT / "agent_tool_benchmark_public_dev_40.json").read_text(encoding="utf-8")
        ))

    def plan(self, dataset):
        return probe.build_plan(
            dataset, model="synthetic-transport-fixture",
            repeat=1, max_output_tokens=384, max_input_tokens=4096,
            max_cost_usd=Decimal("1"), input_usd_per_million=Decimal("1"),
            output_usd_per_million=Decimal("5"), max_requests=40,
        )

    @staticmethod
    def fake_response(*_args, **_kwargs):
        return {
            "object": "response", "id": "FAKE-NOT-PROVIDER-ISSUED",
            "status": "completed",
            "usage": {"input_tokens": 100, "output_tokens": 10},
            "output": [{"type": "function_call", "name": "read_record",
                        "arguments": '{"customer_id":"tenant-a-001"}'}],
        }

    def test_mocked_40_response_recording_with_no_network(self):
        dataset = self.load()
        plan = self.plan(dataset)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic-host-fixture.jsonl"
            with patch.object(probe, "post_response", side_effect=self.fake_response) as mock_http:
                recorded = probe.run_paid(
                    dataset=dataset, plan=plan, result_path=path,
                    max_cost_usd=Decimal("1"),
                    input_rate=Decimal("1"), output_rate=Decimal("5"),
                    approve_paid=True, api_key="FAKE_TEST_KEY_NEVER_ACCEPTED",
                    timeout_seconds=1,
                )
            self.assertEqual(mock_http.call_count, 40)
            self.assertEqual(recorded["provider_requests_recorded"], 40)
            self.assertEqual(recorded["real_tool_dispatches"], 0)
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(len(rows), 40)
            self.assertEqual(len({row["case_id"] for row in rows}), 40)
            self.assertTrue(all(row["provider_response_id"] == "FAKE-NOT-PROVIDER-ISSUED"
                                for row in rows))
            self.assertTrue(all(row["source_type"] ==
                                "DIRECT_RESPONSES_API_FUNCTION_CALL_PROPOSALS"
                                for row in rows))
            self.assertTrue(all(row["judge"]["guard_allowed_proposals"] == 1 for row in rows))
            self.assertTrue(all(row["no_external_dispatch"] for row in rows))
            self.assertTrue(all(row["dataset_sha256"] == plan["dataset_sha256"]
                                for row in rows))
            # A second paid attempt must never overwrite the already captured output.
            with patch.object(probe, "post_response",
                              side_effect=AssertionError("network called")):
                with self.assertRaisesRegex(probe.EvidenceError, "already exists"):
                    probe.run_paid(
                        dataset=dataset, plan=plan, result_path=path,
                        max_cost_usd=Decimal("1"),
                        input_rate=Decimal("1"), output_rate=Decimal("5"),
                        approve_paid=True, api_key="FAKE_TEST_KEY_NEVER_ACCEPTED",
                        timeout_seconds=1,
                    )

    def test_paid_cli_requires_reviewed_dataset_hash(self):
        dataset = self.load()
        with tempfile.TemporaryDirectory() as temp:
            output_path = Path(temp) / "output.jsonl"
            base = [
                "--dataset", str(ROOT / "agent_tool_benchmark_public_dev_40.json"),
                "--model", "test-model", "--max-cost-usd", "1",
                "--input-usd-per-million", "1",
                "--output-usd-per-million", "5",
                "--execute", "--approve-paid", "--result-path", str(output_path),
            ]
            with patch.dict(os.environ, {"OPENAI_API_KEY": "FAKE_TEST_KEY_NEVER_ACCEPTED"}):
                with patch.object(probe, "post_response",
                                  side_effect=AssertionError("network called")):
                    with self.assertRaises(SystemExit) as missing_hash:
                        probe.cli(base)
                    self.assertEqual(missing_hash.exception.code, 2)
                    with self.assertRaises(SystemExit) as wrong_hash:
                        probe.cli(base + ["--expected-dataset-sha256", "0" * 64])
                    self.assertEqual(wrong_hash.exception.code, 2)
            self.assertFalse(output_path.exists())


if __name__ == "__main__":
    unittest.main()
