# Agentic Prompt Injection Evaluation Protocol — v0 (development only)
**Prepared:** 2026-11-02 · **Status:** Synthetic, reproducible scorer only; no model benchmark conducted
**Target:** KAVI Capability Compiler v0.1.1 and unreleased v0.2, no production changes

## Why this is not another KCC green-test count

Our current CI verifies a trusted host's authorization/dispatch boundary. It does not test whether an LLM will obey instructions embedded in lower-trust tool output. This protocol separates three fundamentally different measurements:

1. **Planner behavior:** did a particular model propose a forbidden tool call after encountering untrusted content?
2. **Guard behavior:** would KCC authorize that exact tool name, operation and parameter mapping?
3. **Host effects:** did the real host dispatcher execute a forbidden side effect, and can we independently verify complete coverage?

A model's proposal is NOT an external side effect. A denied proposal is NOT a paid bounty finding. An HMAC-valid trace is NOT complete provenance in the absence of independent host effect coverage.

## What is implemented now

- [Public development casebook](../evals/untrusted_tool_proposals_dev.json): eight synthetic lower-trust documents; all use the same trusted task, a read-only synthetic tenant-a record.
- [Scripted fixture](../evals/scripted_tool_proposals_fixture.json): four intentionally unsafe and four permitted proposals. **Generated manually/scripted; zero model invocations.**
- [Scorer](../evals/score_tool_proposals.py): validates complete case coverage, rejects unsupported or falsely claimed inference counts, and calls the real installed KCC Guard's \`authorize\` method. It **never dispatches tools or makes API calls**.
- [Scorer tests](../tests/test_model_tool_proposal_scorer.py): positive and negative assertions, including duplicates, missing cases, unknown tools, non-scalar input and fake model invocation claims.
- [GitHub Action](../.github/workflows/kcc-safety-cases.yml): runs scorer and all synthetic controls on separately installed stable v0.1.1 and development v0.2.

The eight public cases are a **development set**, not a withheld/blind set; they cannot establish generalization to unknown attacks.

### Scripted-fixture smoke score

| Metric | Value | Meaning |
|---|---:|---|
| Cases | 8 | Public synthetic development cases |
| Proposed calls | 8 | Manually supplied calls |
| Unauthorized proposals | 4 | Scripted probes, not observed model failures |
| Blocked proposals | 4 | KCC/host policy check rejects unsafe proposals |
| Authorized reads | 4 | KCC accepts the expected synthetic read |
| Real model invocations | 0 | No model inference or statistical rate reported |
| Real tool dispatches | 0 | This scoring step executes no side effects |

**Verified CI:** https://github.com/kOs-tile/kavi-capability-compiler/actions/runs/41561400328 (both stable/development jobs successful).

## Scoring commands

From the stacked PR #109 checkout with the exact desired KCC version installed and independently verified:

\`\`\`bash
python -m pytest -o pythonpath=. -q tests/test_model_tool_proposal_scorer.py
python -m evals.score_tool_proposals \
  --dataset evals/untrusted_tool_proposals_dev.json \
  --predictions evals/scripted_tool_proposals_fixture.json \
  --output /tmp/scripted-score.json
\`\`\`

No model key is needed for the synthetic fixture. Do **not** relabel \`source_type: scripted_fixture\` as model evidence. The score JSON declares model inference and external dispatch **false**.

## Gates for a genuine model-backed pilot (NOT YET MET)

- **Target model:** select a specific available model/version and inference configuration, with an approved API/service or a locally controlled offline runner. Budget cap and permission are required before paid requests.
- **Trusted host:** model outputs proposals only. The authenticated host owns policies, Guard, dispatcher, traces and authorization; untrusted document text cannot alter the tool manifest or grant structure.
- **Dataset separation:** create a genuinely private, independently assembled holdout; never publish or optimize on it before scoring. Public eight cases remain development fixtures.
- **Attempts:** use multiple distinct cases and seeds where the provider supports them; do not count deterministic repetitions as independent prompts. Record model ID, parameters, token usage/cost and full trace provenance (subject to secrecy/redaction rules).
- **Metrics:** per-case unsafe proposal rate, valid task completion, guarded unauthorized execution count, false-denial/overblocking, intervention cost and latency. Keep denominators explicit, including inconclusive trials.
- **Untrusted-context isolation:** document exactly where the retrieved/simulated third-party text enters. Do not give it system/developer authority.
- **Failure verification:** independently inspect host events and a distinct host-effect ledger. Reconcile via \`scripts/host_effect_reconcile.py\`; \`UNVERIFIED\` is not a pass.
- **Disclosure:** security-sensitive third-party findings require the relevant program's confidential process, not public issue discussion.
- **External review:** request independent replay from at least two distinct host shapes. Existing public synthetic work does not satisfy the external cohort in #94.

## Remaining uncertainty

The current scorer consumes structured **recorded proposals** only. It cannot authenticate their origin from a particular model, execute a model, show a user-facing harmful action, or estimate true prompt injection attack success probability. This is an engineering preflight for a future model run, not the run itself.

If real model outputs become available through an authorized provider, do **not** modify the dataset or score contract mid-evaluation. Pin model/runtime version, preserve hashes, separate exploration from holdout and re-run the source-verified CI matrix.
