"""Reconstruct scored Groq records independently from the raw client capture.

NO NETWORK and NO tool dispatch. Raw logs are client observations, NOT
cryptographic provider attestations. Synthetic malformed-output rows are
reported as INCONCLUSIVE, never treated as safe responses.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from evals.groq_chat_probe import (
    ALLOWED_MODELS, INGRESS_MODES, OUTPUT_VERSION, SOURCE,
    make_chat_request, parse_chat_completion, parse_dataset, sha256,
    judge_proposals,
)
from evals.openai_responses_probe import EvidenceError, check

RAW_SCHEMA = "kavi.groq-raw-response-ledger.v1"
RAW_SOURCE = "CLIENT_OBSERVED_GROQ_RESPONSE_NOT_PROVIDER_ATTESTED"


def _lines(path: Path) -> list[dict[str, Any]]:
    check(path.is_file(), f"capture missing: {path}")
    check(path.stat().st_size <= 32 * 1024 * 1024,
          "capture exceeds 32 MB inspection limit")
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        check(bool(line.strip()), f"{path}:{line_number} blank row")
        try:
            data = json.loads(line, parse_constant=lambda value: (_ for _ in ()).throw(
                EvidenceError(f"invalid JSON constant: {value}")))
        except json.JSONDecodeError as exc:
            raise EvidenceError(f"{path}:{line_number} invalid JSON") from exc
        check(isinstance(data, dict), "expected JSON object row")
        rows.append(data)
    return rows


def _identity(row: dict[str, Any]) -> tuple[str, str, str, int]:
    model = row.get("model_requested", row.get("model"))
    ingress = row.get("ingress_mode")
    case = row.get("case_id")
    repetition = row.get("repetition")
    check(isinstance(model, str) and model in ALLOWED_MODELS,
          "unknown model in captured row")
    check(ingress in INGRESS_MODES, "unknown ingress in captured row")
    check(isinstance(case, str) and case, "missing case ID")
    check(type(repetition) is int and 0 <= repetition <= 2,
          "invalid repetition")
    return model, ingress, case, repetition


def reconcile(dataset: dict[str, Any], raw_file: Path,
              scored_file: Path) -> dict[str, Any]:
    data = parse_dataset(dataset)
    digest = sha256(data)
    cases = {x["id"]: x for x in data["cases"]}
    raw_rows, scored_rows = _lines(raw_file), _lines(scored_file)
    raw_by_key = {}
    scored_by_key = {}
    for row in raw_rows:
        check(row.get("schema_version") == RAW_SCHEMA and
              row.get("source_type") == RAW_SOURCE,
              "unrecognized raw provider capture")
        model, ingress, case_id, rep = _identity(row)
        key = (model, ingress, case_id, rep)
        check(key not in raw_by_key, "duplicate raw trial")
        check(case_id in cases and row.get("kind") == cases[case_id]["kind"],
              "raw case ID/kind mismatch")
        check(row.get("dataset_sha256") == digest,
              "raw dataset digest mismatch")
        check(row.get("execution_tool_dispatches") == 0,
              "raw record claims external dispatch")
        cap = row.get("max_completion_tokens")
        check(type(cap) is int and 32 <= cap <= 1024,
              "raw output cap invalid")
        expected = sha256(make_chat_request(
            cases[case_id], model=model, ingress_mode=ingress,
            max_completion_tokens=cap))
        check(row.get("request_sha256") == expected,
              "raw request digest does not match current frozen case")
        check(isinstance(row.get("response"), dict),
              "raw provider response must be a JSON object")
        check(row.get("response_sha256") == sha256(row["response"]),
              "raw response digest mismatch")
        raw_by_key[key] = row
    for row in scored_rows:
        check(row.get("schema_version") == OUTPUT_VERSION and
              row.get("source_type") == SOURCE,
              "unrecognized scored capture")
        key = _identity(row)
        check(key not in scored_by_key, "duplicate scored trial")
        check(key in raw_by_key, "scored record without raw source")
        scored_by_key[key] = row

    invalid_raw = []
    matched = []
    for key, raw in raw_by_key.items():
        scored = scored_by_key.get(key)
        try:
            parsed = parse_chat_completion(raw["response"])
        except EvidenceError as exc:
            # The error is a provider-output parsing failure, NOT a safe call.
            check(scored is None,
                  "malformed provider output has a falsely scored record")
            invalid_raw.append({
                "model": key[0], "ingress_mode": key[1],
                "case_id": key[2], "repetition": key[3],
                "category": "unscorable_provider_output",
                "reason": str(exc),
            })
            continue
        check(scored is not None, "valid provider response missing scored record")
        decision = judge_proposals(parsed["proposals"]) if parsed["conclusive"] else None
        expected_values = {
            "model": key[0], "ingress_mode": key[1],
            "case_id": key[2], "kind": raw["kind"], "repetition": key[3],
            "provider_model_reported": parsed["model_reported"],
            "dataset_sha256": raw["dataset_sha256"],
            "request_sha256": raw["request_sha256"],
            "max_completion_tokens": raw["max_completion_tokens"],
            "provider_response_id": parsed["response_id"],
            "finish_reason": parsed["finish_reason"],
            "conclusive": parsed["conclusive"],
            "proposals": parsed["proposals"],
            "guard": decision, "usage": parsed["usage"],
            "external_tool_dispatches": 0,
            "provider_authentication": "CLIENT_OBSERVED_ONLY",
            "free_plan_status": "USER_ATTESTED_NOT_PROVIDER_VERIFIED",
        }
        for field, value in expected_values.items():
            check(scored.get(field) == value,
                  f"raw/scored mismatch for {key[2]}: {field}")
        matched.append(key)

    return {
        "schema_version": "kavi.groq-raw-reconciliation.v1",
        "dataset_sha256": digest,
        "raw_records": len(raw_rows),
        "scored_records": len(scored_rows),
        "reconstructed_scored_records": len(matched),
        "unscorable_raw_records": len(invalid_raw),
        "unscorable": invalid_raw,
        "scored_without_raw": 0,
        "provider_attestation_verified": False,
        "actual_tool_dispatches": 0,
        "limitations": (
            "This detects mismatches between two local client-written logs. "
            "It cannot prove Groq provided the response, that no HTTP failures "
            "occurred before response parsing, or that uninstrumented host "
            "dispatchers do not exist. Invalid raw records are INCONCLUSIVE."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path(__file__).with_name(
        "agent_tool_benchmark_public_dev_40.json"))
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--scored", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.dataset.read_text(encoding="utf-8"))
        report = reconcile(data, args.raw, args.scored)
        blob = json.dumps(report, sort_keys=True, indent=2) + "\n"
        if args.output is not None:
            check(args.output.parent.is_dir() and not args.output.exists(),
                  "summary must use new destination")
            args.output.write_text(blob, encoding="utf-8")
        print(blob, end="")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"raw evidence rejected: {exc}\n")


if __name__ == "__main__":
    main()
