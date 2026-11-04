# KCC Sprint 5 — Groq Free-Tier Agent Tool-Use Evaluation

**Prepared 2026-11-02 · State: code and CI verified, no live inference**

## Decision and scope

We have an existing production Groq integration for the Pulse Fitness chatbot, with a sensitive variable named `PULSE_LLM_API_KEY` on Vercel. **Do not retrieve, rotate, copy, or use that key in this benchmark.** Groq's official rate-limit documentation confirms quota is **organization-level**, not per key or project. Creating a second key inside Pulse's organization alone does not isolate production capacity. A separate verified Free-tier **organization**, or an entirely isolated and explicitly accepted quota policy, is required before the first actual call.

Groq official references:
- [Free plan rate limits](https://console.groq.com/docs/rate-limits): available open-weight models currently include `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, and `qwen/qwen3.8-27b`; published base free limits for these show 30 requests/min, 1000 requests/day and 8000 tokens/minute **per organization**, subject to account-specific exceptions.
- [Local tool calling](https://console.groq.com/docs/tool-use/local-tool-calling) and [API reference](https://console.groq.com/docs/api-reference): `POST https://api.groq.com/openai/v1/chat/completions`, `choices[0].message.tool_calls[].function`.
- [Billing FAQs](https://console.groq.com/docs/billing-faqs): upgrading to Developer makes token usage billable. Stay in **Free** tier; a client-side script cannot independently guarantee the account's tier or invoice status.
- [Projects](https://console.groq.com/docs/projects): projects and keys may still compete for a shared organization-wide quota.

## Implemented in draft PR #109

- `evals/groq_chat_probe.py`: explicit no-network default, vetted model allowlist, tool-call-only proposal ingestion, KCC `Guard.authorize` replay, **zero executed tools**, no production-key fallback, and no paid-tier fallback.
- `evals/agent_tool_benchmark_public_dev_40.json`: 30 synthetic adversarial cases, 10 benign; all are **public development**, not unseen holdout.
- `evals/summarize_groq_run.py`: checks fixed dataset hash, complete trial coverage, request reconstruction, provider IDs, duplicate trials, model outputs, stored Guard decisions, incomplete responses and tool-use counts.
- `tests/test_groq_chat_probe.py`, `tests/test_summarize_groq_run.py`: mocked HTTP transport and evidence-integrity regressions; **zero real Groq requests**.
- `.github/workflows/kcc-safety-cases.yml`: version-isolated CI matrix installing published KCC v0.1.1 and unreleased development v0.2, running all tests without a Groq key.

**Hosted CI proof:** [GitHub Actions run #41590481356](https://github.com/kOs-tile/kavi-capability-compiler/actions/runs/41590481356) — both published stable and development jobs **PASS**, each **70 pytest regression tests** plus scripted no-network checks. These are engineering regressions, not 70 independent security findings.

### Why the scorer can find a problem

This is a **model proposal safety** experiment only. The default `--ingress-mode tool_result` now inserts adversarial content into a **synthetic tool-response message** after a fabricated assistant retrieval-tool history. This models a lower-trust retrieval channel better than placing attacker text in a user message. It is NOT evidence the model itself retrieved a document; no retrieval/network tool is executed. For a separate, differently-labeled comparison, `--ingress-mode user_snippet` preserves the previous user-message representation. Each captured result records the ingress mode. The trusted task is synthetic read of `tenant-a-001`; snippets posing as web content try to induce cross-tenant read, deletion, messaging or argument injection. Groq gets only local function definitions; **no browser_search, code_interpreter, remote MCP, or actual dispatcher** is made available. The host records proposals before KCC checks them. Unexpected tool calls may be present in an API response, but **no tool is executed**. The absence of a model tool call is **not** proof of successful task completion.

## Stage A — no-network preflight (available now)

Use an isolated checkout of the `research/kcc-guard-safety-cases-20261102` branch and a Python 3.11 environment where KCC is installed. This command does **not** need an API key:

```bash
python -m evals.groq_chat_probe \
  --model openai/gpt-oss-20b --ingress-mode tool_result \
  --case-limit 8 --repeat 1 --max-requests 8 \
  > /tmp/groq-free-dry-plan.json
```

Confirm `network_called: false`, `production_key_used: false`, and the reviewed dataset hash:

```
bf2897b9f34ad3c885ee75453a0839ca4e5c7cedeb72a2d4be81a16e1ae11497
```

If the hash differs, stop and review changed test content before making any API request.

## Stage B — only after dedicated Free organization and key exist

1. Verify the account in [Groq Console](https://console.groq.com/): Billing shows **Free** (not Developer) and [Limits](https://console.groq.com/settings/limits) are acceptable. Confirm this organization is not serving Pulse Fitness or any other live production traffic.
2. Create a unique KCC-only test key using [Groq Keys](https://console.groq.com/keys), then put it into the **isolated runner environment** under `GROQ_KCC_API_KEY`. Never paste it into ChatGPT, GitHub issues, PRs or scripts.
3. For an interactive bash session, load the key without printing it or putting its value into command history:

```bash
read -rsp "KCC isolated Free Groq key: " GROQ_KCC_API_KEY
echo
export GROQ_KCC_API_KEY
```

4. Run just eight interleaved attack+benign cases first. This makes **up to 8 actual model API requests** to the separate Free organization; it will not execute any proposed tool:

```bash
python -m evals.groq_chat_probe \
  --model openai/gpt-oss-20b \
  --case-limit 8 --repeat 1 --max-requests 8 \
  --max-completion-tokens 384 --min-interval-seconds 5 \
  --expected-dataset-sha256 bf2897b9f34ad3c885ee75453a0839ca4e5c7cedeb72a2d4be81a16e1ae11497 \
  --execute-free --confirm-org-free-tier \
  --result-path ./groq-20b-pilot-8.jsonl
```

5. Audit the capture, preserving exactly what the provider returned and any failed/missing attempts:

```bash
python -m evals.summarize_groq_run \
  --expected-repetitions 1 \
  ./groq-20b-pilot-8.jsonl \
  --output ./groq-20b-pilot-8-summary.json
```

Each actual inference response is written first to a separate `groq-20b-pilot-8.jsonl.raw-responses.jsonl` **client-captured** ledger with the full provider response and SHA-256, before function-call parsing or Guard scoring. Malformed provider output stops the job without retry, retaining the raw record. This file may contain model output and must be kept private; never commit it to a public repository if real user/customer data is later included. The scorer and raw ledger are separate local artifacts, not independent cryptographic provider attestations.

The report should show 8 recorded and 32 **missing** cases (because it requires the full 40-case grid), and must NOT be labeled a complete benchmark. If the API reports HTTP 429 (quota exceeded), the runner **stops immediately**, without retries or paid fallback. No automatic rerun after partial output.

6. After inspecting real results and account limits, repeat for `qwen/qwen3.8-27b` with a different output file. Only then consider 40 cases per model and eventually 3 repeats each. Do not promise 240 free requests before observing actual per-organization availability and token limits.

## No automation or charges yet

- Existing Pulse Fitness production key: **untouched**.
- Existing KCC OpenAI key: user reports revoked; no calls to OpenAI API performed in this integration.
- Existing Groq KCC-only Free-tier credential: **not provisioned in this execution**.
- Actual Groq inference: **0**, billed Groq usage initiated by this integration: **$0**.
- No automatic GitHub workflow can send Groq API requests; the CI checks are deliberately keyless.
- Metadata-only review of the connected Vercel KCC project entries did not locate a KCC-only Groq credential. The existing Pulse Fitness production secret was not read, copied or used.

## Important scientific limits

- The 40 public development cases were manually written and may be predictable. No independent blinded generalization estimate.
- An HMAC, SHA256 or client-observed API response ID is not independent provider attestation.
- Groq free-plan status is **manually attested** with `--confirm-org-free-tier`; the script cannot query the organization's billing tier.
- Rate limits are shared at the **organization** level even if a separate API key is used.
- The pipeline measures proposed calls, KCC decisions and logging—not real target-system harm or OpenAI product vulnerabilities.
