"""Non-authoritative local demonstration of trace-to-effect reconciliation.

An HMAC-valid trajectory is insufficient to establish dispatch coverage.
Compare the trace to an *independently observed* host side-effect ledger.
Without such an independently trusted ledger, no completeness claim is made.
This checks capability/operation multiplicities, not causality or actor trust.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

class CoverageInputError(ValueError):
    pass

def _dispatch_multiset(events: list[Mapping[str, Any]], *, trace: bool) -> Counter:
    if not isinstance(events, list):
        raise CoverageInputError("event collection must be a list")
    counts = Counter()
    for i, event in enumerate(events):
        if not isinstance(event, Mapping):
            raise CoverageInputError(f"event[{i}] not an object")
        if trace and event.get("kind") != "dispatch":
            continue
        cap, op = event.get("capability_id"), event.get("operation")
        if not isinstance(cap, str) or not cap or not isinstance(op, str) or not op:
            raise CoverageInputError(f"event[{i}] missing capability or operation")
        if trace and event.get("outcome") != "executed":
            raise CoverageInputError(f"event[{i}] invalid dispatch outcome")
        counts[(cap, op)] += 1
    return counts

def compare_trace_to_effects(
    signed_host_bundle: dict[str, Any],
    independent_host_effects: list[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Count reconciliation; cryptographic attestation must be checked first elsewhere.

    A None ledger yields 'UNVERIFIED', never a PASS.
    This does not authenticate ledger origin or guarantee completeness.
    """
    if not isinstance(signed_host_bundle, dict):
        raise CoverageInputError("bundle not an object")
    trace = signed_host_bundle.get("trace")
    if not isinstance(trace, dict) or not isinstance(trace.get("events"), list):
        raise CoverageInputError("bundle has no trace events")
    seen = _dispatch_multiset(trace["events"], trace=True)
    if independent_host_effects is None:
        return {
            "status": "UNVERIFIED",
            "comparison_performed": False,
            "trace_dispatch_count": sum(seen.values()),
            "independent_effect_count": None,
            "unobserved_effect_count": None,
            "phantom_trace_count": None,
            "limitations": "No independent effect ledger supplied. Signature alone does not prove completeness.",
        }
    effects = _dispatch_multiset(independent_host_effects, trace=False)
    unobserved = effects - seen
    phantom = seen - effects
    return {
        "status": "MATCHED_COUNTS_ONLY" if not unobserved and not phantom else "COVERAGE_GAP",
        "comparison_performed": True,
        "trace_dispatch_count": sum(seen.values()),
        "independent_effect_count": sum(effects.values()),
        "unobserved_effect_count": sum(unobserved.values()),
        "phantom_trace_count": sum(phantom.values()),
        "unobserved_effect_kinds": sorted(
            [{"capability_id": cap, "operation": op, "count": n}
             for (cap, op), n in unobserved.items()],
            key=lambda x: (x["capability_id"], x["operation"])),
        "phantom_trace_kinds": sorted(
            [{"capability_id": cap, "operation": op, "count": n}
             for (cap, op), n in phantom.items()],
            key=lambda x: (x["capability_id"], x["operation"])),
        "limitations": "Even matched counts do not establish independent ledger authenticity, causality, missing dispatch paths, external side-effect completion or security certification.",
    }
