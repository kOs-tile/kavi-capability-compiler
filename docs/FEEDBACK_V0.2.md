# v0.2 Feedback Loop

KCC v0.2 is driven by reproducible external failures and integration friction rather than framework-count expansion.

## What we want to learn

The highest-value reports answer one of these questions:

1. Where does KCC require unnecessary glue to sit immediately before a real host dispatcher?
2. Where does the capability model over-block legitimate authority?
3. Where does the model grant, classify, or scope authority more broadly than the task requires?
4. Which capability descriptions produce an unexpected unknown/effect/risk result?
5. Which framework/runtime integration breaks despite fitting an existing generic adapter contract?
6. Which errors are technically fail-closed but operationally too hard to diagnose?

A framework name by itself is not evidence that KCC needs a new framework dependency.

## Minimum reproduction bundle

A useful report should contain:

- KCC version
- Python version
- source format / adapter
- framework/runtime version when relevant
- minimized and redacted capability definition
- minimal task intent and policy fragment when relevant
- expected result
- actual result
- exact command or minimal code path

Prefer a self-contained fixture that can become a regression test.

## Privacy and security

Never include:

- API keys
- bearer tokens
- cookies
- secret headers
- private signing keys
- production credentials
- confidential customer data
- proprietary capability definitions that you are not allowed to disclose

Public issues are for non-sensitive correctness and integration reports.

Use GitHub's private security advisory flow when a report could:

- cause a denied operation to reach the host dispatcher
- bypass approval-required authority
- forge or subvert capsule trust
- expose credentials or secret configuration
- defeat inventory/capsule integrity checks
- turn unknown authority into silent authority

## How v0.2 decisions will be made

A reported case may become v0.2 work when it is reproducible and demonstrates at least one of:

- a security or correctness regression
- repeated integration friction across stacks
- a missing generic contract that cannot be solved cleanly with an existing adapter
- measurable over-blocking or authority broadening
- poor diagnostics that materially slow safe integration

KCC will not add a core dependency or framework-specific primitive solely to increase the number of supported framework logos.

## Evidence discipline

Every accepted security-relevant or authority-semantic bug should produce a regression test before closure.

New benchmark claims must identify whether the evidence is development, holdout, or regression data. Previously exposed holdouts are regression sets and must not be presented as fresh blind evidence.
