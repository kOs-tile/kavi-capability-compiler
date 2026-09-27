# M5 Exit Report

> **Historical checkpoint.** This document records the M5 release-candidate state before the GitHub-first v0.1.0 publication path was finalized. Plain `pip install kavi-capability-compiler` examples below describe the intended future PyPI UX, not the current v0.1.0 install command. For current installation, use `docs/DISTRIBUTION_V0.1.md` or the README. — v0.1 Release Candidate

M5 prepares KAVI Capability Compiler for public distribution without reintroducing framework coupling.

## Release identity

- package: `kavi-capability-compiler`
- version: `0.1.0`
- Python: `>=3.11`
- license: Apache-2.0
- default third-party runtime dependencies: **0**

A current PyPI web search found no indexed project for the exact package name. This is not treated as a reservation guarantee; publication still performs the authoritative registry check.

## Distribution model

Default:

```bash
pip install kavi-capability-compiler
```

Optional:

```bash
pip install "kavi-capability-compiler[mcp]"
pip install "kavi-capability-compiler[signing]"
```

The default wheel does not include KAVI/Hermes/Codex-specific runtime modules.

Historical KAVI validation code remains under `case_studies/` in the repository/source distribution and is not part of the installed core package.

## Public contracts

The v0.1 release-candidate surface is frozen as:

- `kcc.capabilities.v1`
- `kcc.inventory.v1`
- `kcc.inventory-lock.v1`
- `kcc.capsule.v1`
- `kcc.signed-capsule.v1`
- `kcc.execution-evidence.v1`
- `kcc.sdk.v1`

JSON Schemas for the manifest, inventory, inventory lock, execution capsule, and signed-capsule envelope are bundled inside the wheel and available through `get_schema(...)`.

M5.1 additionally makes the runtime fail closed on unsupported capsule versions and on capsules that do not carry `fail_closed=true`, even if their self-integrity digest has been recomputed. Signed envelopes are bound to `kcc.capsule.v1`.

## Integration coverage

Executable integration recipes cover equivalent capability definitions expressed as:

- generic JSON
- MCP
- OpenAI function tools
- Anthropic tools
- OpenAPI

CI marker:

`KCC_INTEGRATION_RECIPES: PASS`

The five formats compile to the same semantic authority and task-scoped grant in the reference integration.

## Release packaging gate

Final M5 release-candidate branch:

- core minimal install: PASS
- wheel build: PASS
- sdist build: PASS
- wheel `--no-deps` install: PASS
- core CLI from installed wheel: PASS
- packaged JSON schemas from installed wheel: PASS
- project-specific KAVI modules absent from installed wheel: PASS
- MCP extra independent install: PASS
- signing extra independent install: PASS
- SHA-256 artifact manifest generation: PASS
- required source-distribution docs/examples/schemas: PASS

## Regression checkpoint

Final M5.1 pre-publication CI checkpoint:

- full suite: **96 passed**
- embedded integration recipes: **PASS**
- core minimal install: **PASS**
- wheel/sdist package smoke: **PASS**
- all five packaged public JSON schemas: **PASS**
- KAVI repo-only case study on `kcc.inventory.v1`: **PASS**
- all compatibility, drift, holdout, authority-reduction, and latency gates: **PASS**
- live MCP discovery integration suite: **11 passed**
- development corpus: **487 capabilities / 30 surfaces**
- development accuracy: **89.73%**
- dangerous recall: **100%**
- false-safe: **0**
- unknown rate: **11.91%**
- overblocking rate: **3.50%**
- sealed post-freeze holdout accuracy: **80.95%**
- sealed holdout dangerous recall: **100%**
- sealed holdout false-safe: **0**
- mean task authority reduction: **99.49%**
- drift recall: **100%**
- authorize p95: approximately **0.0206 ms**
- compile p95: approximately **0.1199 ms**

Latency values are GitHub Actions microbenchmarks, not production throughput guarantees.

## M5 verdict

**RELEASE CANDIDATE HARDENED AND READY FOR FOUNDER-GATED PUBLICATION.**

The codebase is ready to merge as v0.1.0 release-candidate state.

Not yet performed:

- Git tag / GitHub Release publication
- PyPI publication

Those actions are intentionally separate because the available GitHub connector does not expose release/tag creation, and PyPI publication requires an explicitly authorized publishing path.

No paid API or service was used.
