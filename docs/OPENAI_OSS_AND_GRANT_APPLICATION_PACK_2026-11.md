# KAVI OpenAI Application Pack — prepared, not submitted

**Prepared:** November 2, 2026 (America/Chicago).
**Project:** [KAVI Capability Compiler](https://github.com/kOs-tile/kavi-capability-compiler).
**Status:** Internal application draft. No application has been submitted, no funding or credits awarded.
**Source of program terms:** [Codex for Open Source](https://openai.com/form/codex-for-oss/), [OpenAI cybersecurity grant](https://openai.com/form/cybersecurity-grant-program/).

## 1. Codex for Open Source — application fields

| Field | Proposed answer / action |
|---|---|
| GitHub repository | `https://github.com/kOs-tile/kavi-capability-compiler` |
| GitHub username | `kOs-tile` |
| Role | Primary maintainer (validate user's actual role before submission) |
| Select interests | Codex Security; API credits |
| ChatGPT account email | **User confirmation required; do not guess** |
| OpenAI Organization ID | **User/Platform account verification required; do not invent** |
| Personal legal name and contact | **User to confirm** |

**Why does this repository qualify? (max 500 characters; 397 characters)**

> KAVI Capability Compiler is an active, public least-authority SDK for AI agents. Its released v0.1.1 normalizes MCP/OpenAI/Anthropic/OpenAPI tool surfaces into task-scoped grants with pre-dispatch enforcement. Maintainer work includes releases, reproducible CI, issue triage and external feedback requests. This is an early-stage project; broad adoption has not yet been independently established.

**How will you use API credits? (max 500 characters; 330 characters)**

> Use Codex to review OSS pull requests, triage integration reports, turn verified failure cases into regression tests, and analyze authorization-drift changes before releases. API credit usage will be restricted to maintainer workflows and synthetic or permissioned test data. Human reviewers retain release and security decisions.

**Anything else? (max 500 characters; 279 characters)**

> Public technical evidence: KCC v0.1.1 release, 30-MCP-surface development benchmark, and cross-version CI testing 60 scripted pre-dispatch denials plus 10 allowed controls per version. The latter uses only synthetic hosts; no OpenAI vulnerability or third-party audit is claimed.

### Evidence links to attach or cite

- Stable [v0.1.1 README and installation](https://github.com/kOs-tile/kavi-capability-compiler).
- [Cross-version GitHub Actions verification](https://github.com/kOs-tile/kavi-capability-compiler/actions/runs/41559661944): independently installed v0.1.1 and v0.2 development code; 10 allowed and 60 denied test-host operations per channel.
- [Full CI](https://github.com/kOs-tile/kavi-capability-compiler/actions/runs/41559665561): succeeded after immutable action pin repair.
- [Engineering case study draft](https://github.com/kOs-tile/kavi-capability-compiler/blob/research/kcc-guard-safety-cases-20261102/docs/AGENT_AUTHORITY_CROSS_VERSION_CASE_STUDY_2026-11.md).
- [Independent review invitation #103](https://github.com/kOs-tile/kavi-capability-compiler/issues/103) and [external cohort #94](https://github.com/kOs-tile/kavi-capability-compiler/issues/94); **no external review is claimed until it exists**.

### Eligibility risk

OpenAI considers repository usage, adoption, broader ecosystem importance and active maintainer work. Maintenance is supported by the repository's visible releases, CI and issues, but user numbers, stars or downloads **have not been independently verified for this application**. Do not invent them. Credits and any Codex Security eligibility are discretionary and have no guaranteed cash value.

### Submission

Official form: https://openai.com/form/codex-for-oss/

Do not submit until the applicant confirms account email, OpenAI organization ID, actual maintainer role and final language. This document does not create an application automatically.

## 2. Cybersecurity Grant Program — conditional concept

**Decision:** Not submission-ready merely because six deterministic sandbox scenarios pass. OpenAI's current program prioritizes practical and shareable **AI-powered defensive cybersecurity**, especially scalable deployment. A deterministic authorization library by itself may be insufficient. The pilot below adds a human-reviewed AI-assisted workflow without letting an LLM grant authority.

### Proposed project

**Title:** Open Defensive Agent Authority Review — Explain, Detect and Reduce Excess Tool Permissions

**Defensive goal:** Help open-source agent maintainers inventory MCP/API capabilities, detect risky new permissions or tool-contract drift, and propose minimal policies for review. KCC deterministically enforces task-scoped authority at the host dispatcher. An OpenAI API model is used only to summarize evidence, group related tool descriptions, explain drift and draft proposed remediation. The model cannot approve, sign, or expand execution grants.

**Methodology:** collect openly licensed or explicitly authorized public tool manifests; redact secrets and identifiers; define a development/holdout split; compare rule-only classification, AI-assisted human review, and existing maintainer workflows; report dangerous-capability recall, false-safe results, overblocking, reviewer time, cost, and denied versus valid task completion. Blind, previously unseen evaluation sets must stay sealed until scored.

**Potential outputs:** openly licensed synthetic evaluation dataset, reproducible benchmark harness, technical analysis with negative results, safe example policies, and provider-neutral SDK integrations. Fixes to KCC core must follow normal security review and release rules.

**Proposed duration:** 90 days after any approval; no grant-dependent work has started.

**Tier A — $10,000 proposal:** bounded pilot with two documented agent stacks, redacted public manifests, 100–300 independently reviewed candidate cases and repeatable evaluation. Allocation to API usage, dataset review and open-source engineering is illustrative and subject to actual cost validation.

**Tier B — $20,000 proposal:** expand to four stacks and external reviewer validation, audit reproducibility and measure time saved; still only with authorized data and human control of enforcement.

**Need before submission:** concrete model/API availability, cost quotes, participants/reviewer commitments, open-license details, organization/legal identity, a realistic measured pilot and clearer evidence of distribution potential. These are proposals, **not currently achieved outputs or validated budgets**.

Official form: https://openai.com/form/cybersecurity-grant-program/

## 3. Employment positioning (separate channel)

Engineering line for an application **if accurate to the applicant's role**:

> Built an open-source task-scoped authorization compiler for AI agents and validated both a published release and an unreleased development version in isolated CI environments. A host-observed synthetic matrix blocked 60 unauthorized operations per version while allowing 10 valid reads, with exact tool parameters, inventory drift and capsule expiry tested. Documented host bypass and attestation limits rather than claiming a production security certification.

Use the original master CV and role-specific evidence. Bounty disclosures must **not** be conflated with employment applications. Actual OpenAI job applications must go through official Careers. No job interview, referral, bounty reward or OpenAI endorsement has been received.

## 4. Approval gates

- Confirm active public maintainer identity and account association.
- Confirm the form fields and policies at actual submission.
- Do not disclose nonpublic vulnerability details.
- Do not use customer, third-party, or proprietary data without permission.
- Do not state unverified adoption, independent security review, funded grant or guaranteed credits.
