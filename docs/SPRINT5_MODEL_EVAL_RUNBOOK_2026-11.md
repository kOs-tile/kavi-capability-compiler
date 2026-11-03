# Sprint 5 — Model-backed agent safety evaluation runbook

**Prepared:** 2026-11-02 (America/Chicago)
**Status:** PRE-FLIGHT PASSED — ZERO LIVE MODEL INFERENCES
**Scope:** Public synthetic development set, not private holdout or OpenAI vulnerability testing
**Code:** \`evals/openai_responses_probe.py\`, \`evals/summarize_responses_run.py\`, \`evals/agent_tool_benchmark_public_dev_40.json\`

## Actual engineering status

- 30 synthetic adversarial snippets and 10 benign snippets added and version-controlled as PUBLIC DEVELOPMENT, not hidden/test holdout.
- Model responses can be ingested directly from the OpenAI **Responses API** \`output[].type == "function_call"\`, with each proposed tool name and JSON argument mapping recorded.
- KCC Guard \`authorize\` independently evaluates proposals; the benchmark tool **never calls the proposed dispatcher**.
- The executable runner requires explicit \`--execute\` and \`--approve-paid\`, a non-empty \`OPENAI_API_KEY\`, a reviewed exact dataset SHA-256 and a new output path. Without these, it stays in no-network planning mode.
- Every recorded response includes request digest, dataset digest, provider response ID, model request, status, token usage, local price estimate and KCC decision. Logs are append-only JSONL with file sync; file overwrite is refused.
- The evidence summarizer refuses mismatched request hashes, duplicates, wrong dataset/kind/source and inconsistent judgment totals. Missing trials and incomplete responses are NOT silently counted as safe or successful.
- A full 40-response **mock HTTP** stream runs in CI with *no network*. The fake responses are not model results.
- Both published stable KCC v0.1.1 and unreleased development v0.2 must pass the test suite with different installed import paths.

**Latest verified CI:** https://github.com/kOs-tile/kavi-capability-compiler/actions/runs/41563832966 — both jobs PASS, 39 tests per development job at this checkpoint. Tests are engineering regressions, not 39 new security vulnerabilities.

## Proposed actual pilot — 240 responses if access is approved

Two models from official OpenAI API model catalog as of November 2, 2026:

| Model | Trials | Public rate / 1M input tokens | Public rate / 1M output tokens | Local token-envelope estimate |
|---|---:|---:|---:|---:|
| \`gpt-6-luna\` | 120 | $0.10 | $0.50 | $0.110592 |
| \`gpt-6.1-sol\` | 120 | $2.00 | $10.00 | $2.211840 |
| **Total** | **240 planned** | | | **$2.322432** |

Model pricing reference (Standard short-context, without separate tool calls): https://developers.openai.com/api/docs/pricing. These are **calculations** assuming at most 4,096 billed input and 1,024 billed output tokens per request, no regional/priority surcharge or extra provider fees. They are NOT actual token usage, an invoice or a true hard spending cap. Lower output-token limits may truncate reasoning and make trials inconclusive; increasing the cap changes the budget estimate. Verify current pricing and model access immediately before running. The $20 research budget can be partitioned as a $10 local cap **per model**, not automatic authorization to spend.

### Step 1 — build two no-network previews

Use an isolated checkout of the stacked draft PR #109, Python 3.11+ and the desired verified KCC version. Do **not** expose API keys in shell history, logs or GitHub issues.

\`\`\`bash
python -m evals.openai_responses_probe \
  --model gpt-6-luna --repeat 3 --max-requests 120 \
  --max-input-tokens 4096 --max-output-tokens 1024 \
  --max-cost-usd 10 --input-usd-per-million 0.10 \
  --output-usd-per-million 0.50 > plan-luna.json

python -m evals.openai_responses_probe \
  --model gpt-6.1-sol --repeat 3 --max-requests 120 \
  --max-input-tokens 4096 --max-output-tokens 1024 \
  --max-cost-usd 10 --input-usd-per-million 2.00 \
  --output-usd-per-million 10.00 > plan-sol.json
\`\`\`

Review \`dataset_sha256\` and \`whole_plan_estimated_ceiling_usd\` in these previews. Both previews cost **$0** and do not contact the API.

### Step 2 — paid execution only with intentional user approval and credential setup

**NOT DONE.** Only after the user explicitly authorizes spending and sets a restricted \`OPENAI_API_KEY\` in the runner's execution environment (never in the repository):

\`\`\`bash
# Copy the exact independently reviewed 64-character hash from plan-luna.json.
# DO NOT use auto-discovered current SHA to silently bypass the pin check.
REVIEWED_SHA256="<copy_the_verified_dataset_sha256>"

python -m evals.openai_responses_probe \
  --model gpt-6-luna --repeat 3 --max-requests 120 \
  --max-input-tokens 4096 --max-output-tokens 1024 \
  --max-cost-usd 10 --input-usd-per-million 0.10 \
  --output-usd-per-million 0.50 \
  --execute --approve-paid --expected-dataset-sha256 "$REVIEWED_SHA256" \
  --result-path ./approved-luna.jsonl

python -m evals.openai_responses_probe \
  --model gpt-6.1-sol --repeat 3 --max-requests 120 \
  --max-input-tokens 4096 --max-output-tokens 1024 \
  --max-cost-usd 10 --input-usd-per-million 2.00 \
  --output-usd-per-million 10.00 \
  --execute --approve-paid --expected-dataset-sha256 "$REVIEWED_SHA256" \
  --result-path ./approved-sol.jsonl
\`\`\`

This script only **proposes** and judges function calls. It never executes read/delete/send on any customer system. Set a provider-side spend cap separately if supported. An error after an HTTP response may still incur an unlogged provider charge; reconcile platform billing independently. Do not treat CLI "local cap" as a provider guarantee.

### Step 3 — audit and compare complete logs

\`\`\`bash
python -m evals.summarize_responses_run \
  --expected-repetitions 3 \
  approved-luna.jsonl approved-sol.jsonl \
  --output ./approved-summary.json
\`\`\`

The summarizer requires all 40 cases for each repetition to call a run complete. It reports absent and inconclusive cases separately, as well as unsafe function proposals, blocked proposals and correct benign read proposals. Exact proportions are conditional on completed responses, **not** independent attack success probabilities.

### Evidence trust contract

1. **Model proposal:** Model function-call output is treated as untrusted and parsed, not executed.
2. **Guard authorization:** KCC computes a decision against a deterministic capsule and known tool inventory. The host still must enforce that decision at each dispatcher.
3. **Host side effect:** There is intentionally **no** dispatcher call in this pilot. Actual side-effect safety of a live host requires separate independently protected host instrumentation.
4. **Provenance:** Client-observed provider response IDs are not cryptographically signed and cannot alone prove provider authenticity. Do not mislabel simulated replay rows as live-provider results.
5. **Blind holdout:** This set is public development data; a true withheld evaluation requires separate, independently curated prompts and a frozen decision rule.

## Current blockers before any paid run

- No OpenAI API credential or approved model account has been validated in this execution environment.
- User has not separately authorized the actual $20 maximum spend in this chat; previous "$20" was a planning ceiling, not a payment instruction.
- No authentic model responses or independent third-party reviewers have been obtained.
- #104, #107 and #109 remain drafts. No production rollout or bounty report.

## Source references

- OpenAI Responses API reference (function-call outputs, usage, storage, model selection): https://developers.openai.com/api/reference/resources/responses/methods/create
- OpenAI model catalog: https://developers.openai.com/api/docs/models
- OpenAI API pricing: https://developers.openai.com/api/docs/pricing

**No security claim is stronger than the evidence above.**
