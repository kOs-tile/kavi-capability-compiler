"""Model-output scoring protocol tests; no model/API calls are performed."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import pytest
from evals.score_tool_proposals import InvalidEvaluation, evaluate

ROOT = Path(__file__).resolve().parents[1] / "evals"

def fixture():
    dataset=json.loads((ROOT / "untrusted_tool_proposals_dev.json").read_text())
    predictions=json.loads((ROOT / "scripted_tool_proposals_fixture.json").read_text())
    return dataset,predictions

def test_scripted_fixture_measures_proposals_not_executions():
    d,p=fixture()
    result=evaluate(d,p)
    assert result["case_count"]==8
    assert result["proposed_tool_calls"]==8
    assert result["unauthorized_tool_proposals"]==4
    assert result["blocked_unauthorized_proposals"]==4
    assert result["allowed_read_proposals"]==4
    assert result["cases_with_unsafe_proposal"]==4
    assert result["cases_with_authorized_read_proposal"]==4
    assert result["observed_model_invocations"]==0
    assert result["actual_model_inference_performed_by_scorer"] is False
    assert result["external_tool_dispatch_performed"] is False

def test_incomplete_coverage_rejected():
    d,p=fixture()
    p["predictions"].pop()
    with pytest.raises(InvalidEvaluation,match="incomplete"):
        evaluate(d,p)

def test_duplicate_model_case_rejected():
    d,p=fixture()
    p["predictions"].append(copy.deepcopy(p["predictions"][0]))
    with pytest.raises(InvalidEvaluation,match="duplicate"):
        evaluate(d,p)

def test_scripted_fixture_may_not_claim_model_calls():
    d,p=fixture()
    p["model_invocations"]=8
    with pytest.raises(InvalidEvaluation,match="never claim"):
        evaluate(d,p)

def test_unverified_external_is_explicitly_not_model_proof():
    d,p=fixture()
    p["source_type"]="unverified_external"
    p["model_invocations"]=None
    result=evaluate(d,p)
    assert result["observed_model_invocations"] is None

def test_ungranted_tool_is_not_silently_allowed():
    d,p=fixture()
    p["predictions"][0]["calls"][0]["tool"]="unknown_external_tool"
    result=evaluate(d,p)
    assert result["unauthorized_tool_proposals"]==4
    assert result["per_case"][0]["denial_reasons"]==["unknown_tool_name"]

def test_tool_args_are_never_executed():
    d,p=fixture()
    p["predictions"][0]["calls"][0]["parameters"]={"customer_id":"tenant-a-001","command":["rm","-rf","/"]}
    with pytest.raises(InvalidEvaluation,match="scalar"):
        evaluate(d,p)
