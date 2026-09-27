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
