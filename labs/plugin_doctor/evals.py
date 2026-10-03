from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence

EVAL_REPORT_VERSION = "plugin-doctor.invocation-eval.v0"

_STOP = {
    "a", "an", "and", "for", "from", "in", "is", "it", "my", "of", "on", "please",
    "the", "this", "to", "with", "me", "can", "you", "i",
}


@dataclass(frozen=True)
class InvocationCase:
    case_id: str
    prompt: str
    expected_tools: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()


ToolSelector = Callable[[str, Sequence[Mapping[str, Any]]], Sequence[str]]


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 1 and token not in _STOP
    }


def lexical_selector(prompt: str, tools: Sequence[Mapping[str, Any]]) -> list[str]:
    """Deterministic baseline selector for CI; not a model-behavior claim."""

    prompt_tokens = _tokens(prompt)
    ranked: list[tuple[float, str]] = []
    for tool in tools:
        name = str(tool.get("name") or "")
        description = str(tool.get("description") or "")
        tool_tokens = _tokens(name.replace("_", " ") + " " + description)
        if not tool_tokens:
            continue
        overlap = len(prompt_tokens & tool_tokens)
        if overlap == 0:
            continue
        score = overlap / math.sqrt(max(1, len(tool_tokens)))
        name_tokens = _tokens(name.replace("_", " "))
        score += 0.75 * len(prompt_tokens & name_tokens)
        ranked.append((score, name))

    if not ranked:
        return []
    ranked.sort(key=lambda item: (-item[0], item[1]))
    best = ranked[0][0]
    if best < 0.45:
        return []
    return [name for score, name in ranked if score >= best * 0.92]


def run_invocation_evals(
    tools: Sequence[Mapping[str, Any]],
    cases: Iterable[InvocationCase],
    *,
    selector: ToolSelector = lexical_selector,
    runner_name: str = "lexical-baseline",
) -> dict[str, Any]:
    """Run positive/negative tool-selection cases through an injectable selector.

    Production can replace the selector with a real model runner while CI keeps a
    deterministic baseline.
    """

    known = {str(tool.get("name") or "") for tool in tools}
    rows = []

    for case in cases:
        expected = set(case.expected_tools)
        forbidden = set(case.forbidden_tools)
        unknown_refs = sorted((expected | forbidden) - known)
        if unknown_refs:
            raise ValueError(f"Eval case {case.case_id} references unknown tools: {unknown_refs}")

        selected = list(dict.fromkeys(str(name) for name in selector(case.prompt, tools)))
        selected_set = set(selected)
        missing = sorted(expected - selected_set)
        forbidden_selected = sorted(forbidden & selected_set)
        passed = not missing and not forbidden_selected

        rows.append(
            {
                "case_id": case.case_id,
                "prompt": case.prompt,
                "expected_tools": sorted(expected),
                "forbidden_tools": sorted(forbidden),
                "selected_tools": selected,
                "missing_expected": missing,
                "forbidden_selected": forbidden_selected,
                "passed": passed,
            }
        )

    passed_count = sum(1 for row in rows if row["passed"])
    total = len(rows)
    return {
        "version": EVAL_REPORT_VERSION,
        "runner": runner_name,
        "total": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "pass_rate": (passed_count / total) if total else 1.0,
        "cases": rows,
        "disclaimer": "The default lexical baseline is a deterministic CI signal, not a measurement of ChatGPT invocation behavior.",
    }
