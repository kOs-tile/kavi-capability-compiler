# Plugin Doctor V0 incubation

This directory is an isolated product experiment built on top of KCC.

It must not change KCC compiler or Guard semantics.

Run the initial tests from the repository root:

```bash
pytest -q labs/plugin_doctor/tests
```

The first slice accepts capability definitions already supported by KCC and emits a deterministic static-readiness report.

See `docs/PLUGIN_DOCTOR_V0.md` for the product contract.
