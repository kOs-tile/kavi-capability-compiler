# v0.1 Release Checklist

## Code
- [x] main contains the M0–M4 shipped implementation
- [x] package version and `__version__` both equal 0.1.0
- [x] public `__all__` contract is explicit and framework-neutral
- [x] `kcc.capabilities.v1`, `kcc.inventory.v1`, `kcc.inventory-lock.v1`, `kcc.capsule.v1`, and `kcc.sdk.v1` are explicitly versioned
- [x] full test suite passes at the current release-candidate checkpoint
- [x] all benchmark safety gates pass
- [x] adversarial SDK benchmark is CI-gated
- [x] inventory-bound Guard rejects post-compile capability drift
- [x] OpenAI Agents SDK 0.22.3 real FunctionTool boundary is CI-gated
- [x] Anthropic Python SDK 1.8.0 real beta-tool boundary is CI-gated
- [x] LangGraph 1.2.12 real ToolNode boundary is CI-gated

## Packaging
- [x] wheel builds
- [x] sdist builds
- [x] wheel installs with `--no-deps`
- [x] core SDK imports from the installed wheel
- [x] core CLI works from the installed wheel
- [x] all five public JSON schemas load from the installed wheel
- [x] KAVI/Hermes/Codex-specific runtime modules are absent from the installed core wheel
- [x] `mcp` extra installs independently
- [x] `signing` extra installs independently
- [x] Apache-2.0 license metadata/file and Python >=3.11 are declared
- [x] artifact SHA-256 checksums are generated during release CI
- [x] all five framework-neutral integration kits are present in the source distribution
- [x] release CI builds twice from one commit-derived SOURCE_DATE_EPOCH, canonicalizes sdist archive metadata to that epoch, and requires identical wheel + sdist SHA-256 outputs
- [x] release metadata is checked with Twine
- [x] installed wheel is checked to exclude repository-only case studies, examples, benchmarks, tests, docs, and scripts

## Documentation
- [x] README describes v0.1 behavior
- [x] embedded SDK guide is current
- [x] universal manifest guide is current
- [x] SDK compatibility and exception semantics are documented
- [x] framework-neutral execution-evidence contract is current
- [x] benchmark report includes limitations
- [x] integration examples execute in CI
- [x] Generic Python, OpenAI-shaped, Anthropic-shaped, MCP-shaped, and OpenAPI kits execute without vendor credentials
- [x] framework-specific validation targets are separated from the installed core
- [x] external runtime validation evidence and limitations are consolidated in `docs/EXTERNAL_VALIDATION_V0.1.md`

## Publication
- [x] GitHub-first release workflow is manual, exact-main-SHA gated, version-confirmed, and requires prior green main CI
- [x] release build job has no repository write or OIDC permission
- [x] only the GitHub Release job has `contents: write`
- [x] release payload is reproducibility-checked, Twine-checked, clean-installed, checksummed, and Simple-Index validated before publication
- [x] Simple Repository links bind release assets with SHA-256 fragments
- [x] GitHub Pages deployment is isolated in a separate manual workflow and cannot affect GitHub Release success
- [x] create `v0.1.0` tag + GitHub Release from the final verified main SHA
- [x] attach the verified wheel, sdist, and `SHA256SUMS`
- [ ] enable GitHub Pages with GitHub Actions as source
- [ ] deploy the Simple Repository index from the immutable v0.1.0 release assets
- [ ] later mirror the exact same v0.1.0 artifacts to PyPI when account registration is available
- [x] public wheel and sdist digests match the verified publish-run artifacts
- [x] clean install verifies version `0.1.0`, `kcc.sdk.v1`, CLI, Guard, and all five public schemas
- [x] release workflow uses draft -> verified asset attachment -> publish sequencing
- [ ] enable GitHub Immutable Releases protection before the next release cycle
- [x] do not rebuild v0.1.0 for PyPI
- [x] do not claim production certification or universal framework support


## v0.1.1 security patch

- [x] parameter-rule hardening merged to main
- [x] unsupported/malformed structured predicates fail closed at compile time
- [x] incompatible runtime numeric/length bound values fail closed deterministically
- [x] public SDK and data-contract versions remain unchanged
- [x] release tooling derives package version/tag/artifact names from pyproject metadata
- [x] Pages tooling derives the current release version/tag
- [x] PR test workflow fully green
- [x] PR release dry-run fully green
- [x] post-merge main test fully green
- [x] final manual publish dry-run artifact payload verified
- [x] publish immutable v0.1.1 GitHub Release from exact green main SHA
- [x] deploy the Simple Repository index from v0.1.1
- [x] rerun external consumer, diagnostics, and optional-extras evidence against v0.1.1
- [x] update current public install/status docs to v0.1.1 after publication
- [x] do not rebuild v0.1.1 for a later PyPI mirror


## v0.2.0 release

- [x] main version identity moved off published v0.1.1 after additive public API expansion
- [x] `pyproject.toml` and `kcc.__version__` identify main as 0.2.0
- [x] latest stable/public install documentation continues to target v0.1.1
- [x] external public dogfood defaults continue to target v0.1.1 until v0.2.0 is published
- [x] delegation attenuation design/provenance gates completed
- [x] bounded deterministic delegation core merged with full green main CI
- [x] candidate v0.2 RC scope frozen without closing the external-feedback gate
- [ ] collect external feedback on v0.2 development behavior
- [ ] decide final v0.2 release scope from evidence
- [ ] final v0.2 test workflow fully green
- [ ] final v0.2 release dry-run fully green
- [ ] publish only from an exact green main SHA after explicit manual confirmation
