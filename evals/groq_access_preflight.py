"""Non-inference Groq Free organization access preflight.

Default is an offline plan (zero network calls). Live mode performs only
read-only GET /models and GET /models/{id} with the isolated KCC secret.
No model completion, no billing-tier claim, no production-key fallback.
Provider error messages and arbitrary response fields never reach stdout.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from typing import Any

from evals.groq_chat_probe import ALLOWED_MODELS
from evals.groq_curl_transport import request_json as curl_request_json
from evals.openai_responses_probe import EvidenceError, check

MODELS_URL = "https://api.groq.com/openai/v1/models"
SAFE_ID_MAX = 100


def get_json(url: str, key: str, *, timeout: int = 15) -> dict[str, Any]:
    check(url == MODELS_URL or
          url in (MODELS_URL + "/" + model for model in ALLOWED_MODELS),
          "only known Groq model metadata endpoints permitted")
    check(type(timeout) is int and 1 <= timeout <= 30,
          "invalid metadata timeout")
    # GET metadata must use the exact same curl TLS/HTTP stack as inference.
    # No raw provider body, user token, or OAuth data is printed.
    return curl_request_json(
        method="GET", url=url, key=key, timeout_seconds=timeout,
    )


def inspect_models(key: str, *, model: str = "openai/gpt-oss-20b",
                   request_fn=get_json) -> dict[str, Any]:
    check(model in ALLOWED_MODELS, "unsupported model")
    response = get_json(MODELS_URL, key) if request_fn is get_json else request_fn(MODELS_URL, key)
    check(response.get("object") == "list" and
          isinstance(response.get("data"), list),
          "invalid Groq model-list schema")
    available = set()
    for item in response["data"]:
        if isinstance(item, dict):
            ident = item.get("id")
            if isinstance(ident, str) and ident in ALLOWED_MODELS and item.get("active") is not False:
                available.add(ident)
    # The models API lists ACTIVE models; it may not establish that the
    # caller has permission to use each, so do not equate membership with access.
    summary = {
        "schema_version": "kavi.groq-free-model-metadata.v1",
        "non_inference_metadata_requests": 1,
        "model_checked": model,
        "catalog_contains_target": model in available,
        "approved_models_visible": sorted(available),
        "model_detail_verified": False,
        "permissions_independently_verified": False,
        "billing_tier_independently_verified": False,
        "real_model_completions": 0,
        "external_tool_dispatches": 0,
    }
    if model not in available:
        summary["next_step"] = "Target model is absent from metadata; STOP and check account/project."
        return summary
    detail = get_json(MODELS_URL + "/" + model, key) if request_fn is get_json else request_fn(MODELS_URL + "/" + model, key)
    summary["non_inference_metadata_requests"] = 2
    summary["model_detail_verified"] = bool(
        isinstance(detail.get("id"), str) and detail["id"] == model and detail.get("active") is not False
    )
    summary["next_step"] = (
        "Model metadata accessible; NOT proof completion permissions are granted."
        if summary["model_detail_verified"] else
        "Model detail inconsistent; STOP."
    )
    return summary


def cli(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=ALLOWED_MODELS,
                        default="openai/gpt-oss-20b")
    parser.add_argument("--execute-free-readonly", action="store_true")
    parser.add_argument("--confirm-isolated-free-org", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute_free_readonly:
        check(not args.confirm_isolated_free_org,
              "confirmation is valid only for executed metadata check")
        return {
            "mode": "no_network_dry_plan",
            "endpoint": MODELS_URL,
            "model": args.model,
            "network_called": False,
            "model_completions": 0,
        }
    check(args.confirm_isolated_free_org,
          "requires confirmation of a dedicated Free organization")
    key = os.environ.get("GROQ_KCC_API_KEY", "")
    return inspect_models(key, model=args.model)


if __name__ == "__main__":
    try:
        print(json.dumps(cli(), sort_keys=True, indent=2))
    except (EvidenceError, OSError, ValueError) as err:
        # Our classified EvidenceError is allowlisted; never print provider raw text.
        raise SystemExit("Groq metadata preflight blocked: " + str(err)) from None
