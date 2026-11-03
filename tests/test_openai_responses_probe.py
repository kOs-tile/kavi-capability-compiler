"""Offline preflight and paid-execution guard tests. Never calls live APIs."""
import json
import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from evals import openai_responses_probe as e


class TestSprint5Runner(unittest.TestCase):
    @staticmethod
    def dataset():
        return {
            "schema_version": e.SCHEMA,
            "visibility": "PUBLIC_DEVELOPMENT_NOT_BLIND_HOLDOUT",
            "trust_boundary": "UNTRUSTED_SNIPPET_IN_USER_MESSAGE",
            "allowed_tool_call": {"tool": "read_record",
                                  "parameters": {"customer_id": "tenant-a-001"}},
            "case_counts": {"attack": 30, "benign": 10},
            "cases": [
                {"id": f"A{i:02}", "kind": "attack", "untrusted_text": f"synthetic attack {i}"}
                for i in range(30)
            ] + [
                {"id": f"B{i:02}", "kind": "benign", "untrusted_text": f"synthetic safe {i}"}
                for i in range(10)
            ],
        }

    def test_dataset_counts(self):
        self.assertEqual(len(e.parse_dataset(self.dataset())["cases"]), 40)

    def test_dataset_duplicate_rejected(self):
        data = self.dataset()
        data["cases"][1]["id"] = data["cases"][0]["id"]
        with self.assertRaisesRegex(e.EvidenceError, "duplicate"):
            e.parse_dataset(data)

    def test_not_holdout(self):
        data = self.dataset()
        data["visibility"] = "PRIVATE_HOLDOUT"
        with self.assertRaisesRegex(e.EvidenceError, "not public development"):
            e.parse_dataset(data)

    def test_dataset_sha_stable(self):
        data = self.dataset()
        self.assertEqual(e.sha256(data), e.sha256(json.loads(json.dumps(data))))

    def test_request_no_real_tools(self):
        request = e.make_request(self.dataset()["cases"][0],
                                 model="test-model", max_output_tokens=384)
        self.assertEqual(request["tool_choice"], "auto")
        self.assertFalse(request["parallel_tool_calls"])
        self.assertFalse(request["store"])
        self.assertEqual({v["name"] for v in request["tools"]},
                         {"read_record", "delete_record", "send_message"})

    def test_function_parser(self):
        result = {"output": [{"type": "message", "content": []}, {
            "type": "function_call", "name": "read_record",
            "arguments": '{"customer_id":"tenant-a-001"}',
        }]}
        self.assertEqual(e.extract_function_calls(result), [
            {"tool": "read_record", "parameters": {"customer_id": "tenant-a-001"}}
        ])

    def test_reject_non_object_tool_args(self):
        with self.assertRaisesRegex(e.EvidenceError, "not a mapping"):
            e.extract_function_calls({"output": [{
                "type": "function_call", "name": "read_record", "arguments": "[1]",
            }]})

    def test_reject_malformed_tool_json(self):
        with self.assertRaisesRegex(e.EvidenceError, "invalid function JSON"):
            e.extract_function_calls({"output": [{
                "type": "function_call", "name": "read_record", "arguments": "garbage",
            }]})

    def test_usage_missing(self):
        with self.assertRaisesRegex(e.EvidenceError, "missing token usage"):
            e.usage_of({"output": []})

    def test_usage_bool_rejected(self):
        with self.assertRaisesRegex(e.EvidenceError, "invalid provider usage"):
            e.usage_of({"usage": {"input_tokens": True, "output_tokens": 12}})

    def test_budget_estimate(self):
        self.assertEqual(e.bill_usd((1000, 100), Decimal("1"), Decimal("10")),
                         Decimal(".002"))

    def test_negative_budget(self):
        with self.assertRaisesRegex(e.EvidenceError, "must be positive"):
            e.usd("-1")

    def test_plan_240_for_two_separate_models(self):
        d = e.parse_dataset(self.dataset())
        p = e.build_plan(d, model="model-a", repeat=3, max_output_tokens=384,
                         max_input_tokens=4096, max_cost_usd=Decimal("20"),
                         input_usd_per_million=Decimal("10"),
                         output_usd_per_million=Decimal("40"), max_requests=120)
        self.assertEqual(p["request_count"], 120)
        self.assertFalse(p["network_called"])

    def test_plan_fails_insufficient_max_requests(self):
        with self.assertRaisesRegex(e.EvidenceError, "max requests"):
            e.build_plan(self.dataset(), model="model-a", repeat=3,
                         max_output_tokens=384, max_input_tokens=4096,
                         max_cost_usd=Decimal("20"),
                         input_usd_per_million=Decimal("10"),
                         output_usd_per_million=Decimal("40"), max_requests=40)

    def test_budget_fails_ceiling(self):
        with self.assertRaisesRegex(e.EvidenceError, "price envelope exceeds budget"):
            e.build_plan(self.dataset(), model="model-a", repeat=1,
                         max_output_tokens=1024, max_input_tokens=16000,
                         max_cost_usd=Decimal(".01"),
                         input_usd_per_million=Decimal("100"),
                         output_usd_per_million=Decimal("100"), max_requests=40)

    def test_cli_preview_never_calls_network(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dataset.json"
            path.write_text(json.dumps(self.dataset()))
            with patch.object(e, "post_response",
                              side_effect=AssertionError("network called")):
                result = e.cli([
                    "--dataset", str(path), "--model", "test-model",
                    "--max-cost-usd", "20", "--input-usd-per-million", "1",
                    "--output-usd-per-million", "5",
                ])
            self.assertEqual(result["request_count"], 40)
            self.assertFalse(result["network_called"])

    def test_execute_without_key_cannot_start(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dataset.json"
            path.write_text(json.dumps(self.dataset()))
            out = Path(temp) / "output.jsonl"
            with self.assertRaises(SystemExit) as failure:
                with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
                    e.cli([
                        "--dataset", str(path), "--model", "test-model",
                        "--max-cost-usd", "20", "--input-usd-per-million", "1",
                        "--output-usd-per-million", "5",
                        "--execute", "--approve-paid", "--result-path", str(out),
                    ])
            self.assertEqual(failure.exception.code, 2)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
