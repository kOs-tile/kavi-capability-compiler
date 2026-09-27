# Contributing

KCC is built around measurable least-authority behavior rather than framework-specific control logic.

## Development setup

```bash
python -m pip install -e ".[all]"
python -m pip install pytest
pytest -q
```

## Design rules

1. Keep the compiler core framework-neutral.
2. Prefer adapters or `kcc.capabilities.v1` over modifying an external agent runtime.
3. Never make missing metadata imply safety.
4. Treat source annotations as evidence, not unquestioned authorization.
5. Do not tune benchmark classifiers merely to improve headline accuracy.
6. Preserve provenance separately from semantic authority fingerprints.
7. Denied runtime calls must not reach the host dispatcher.
8. Optional integrations must not become required dependencies of the default install.
9. Add a regression test for every security-relevant bug.
10. Public benchmark claims must identify whether data is development, holdout, or regression evidence.

## Reporting feedback and bugs

For v0.2, feedback should be reproducible and privacy-safe.

Include the smallest useful reproduction:
- KCC version and Python version
- source format or adapter used
- relevant framework/runtime version, if any
- a minimized/redacted capability definition
- task intent and policy fragment needed to reproduce
- expected authority/effect/risk result
- actual result
- exact command or minimal code path

Never include API keys, bearer tokens, cookies, private repository credentials, secret headers, or production-only proprietary data.

If the behavior could allow a denied operation to reach the host dispatcher, expose secrets, forge a signed capsule, bypass approval, or otherwise cross a security boundary, do not file it publicly. Use the repository's private security advisory flow.

See `docs/FEEDBACK_V0.2.md`.

## Pull requests

A change is ready when:

- focused tests pass
- full CI passes
- new public API is documented
- package dependency changes are justified
- framework-specific behavior stays outside the core unless it is part of a generic adapter contract

## Adding an integration

Prefer one of two forms:

- convert the external tool definition into an existing built-in adapter format; or
- emit `kcc.capabilities.v1` directly

A new framework name alone is not sufficient reason to add a core dependency.

## Development execution discipline

KCC development should optimize for evidence quality and iteration throughput at the same time.

1. Work on one milestone branch from fresh `main`.
2. Prepare a coherent batch of related file changes before writing Git history.
3. Prefer one atomic Git tree/commit for that batch instead of one commit per file.
4. Open or update one pull request and let PR CI be the branch verification surface.
5. A newer PR commit supersedes older CI; stale runs are cancelled automatically.
6. When CI fails, inspect the exact failing job/step first, then make one bounded repair commit.
7. Do not make speculative micro-commits while a previous full CI run is still executing.
8. Keep the complete security, benchmark, package, and compatibility gates intact.
9. Merge with squash unless preserving separate commits has a concrete review or release value.
10. Treat the post-merge `main` CI run as the authoritative final verification.

Operationally, this means the preferred loop is:

`fresh main -> coherent batch -> one commit -> PR CI -> diagnosed repair if needed -> green -> squash merge -> main CI`

This workflow reduces queueing and duplicate CI without weakening any release or security gate.
