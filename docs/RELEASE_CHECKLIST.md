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
- [x] public capsule verification rejects tampered inventory integrity
- [x] inventory-lock drift checks reject tampered lock/current-inventory integrity
- [x] authenticated non-loopback MCP HTTP discovery requires HTTPS and URL userinfo is rejected

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
- [x] source distribution excludes repository-only KAVI/framework validation case studies
- [x] CI actions are pinned to immutable commit SHAs and checkout credentials are not persisted
- [x] release verification toolchain is version-pinned
- [x] zero-dependency security preflight checks workflow refs and obvious secret material
- [x] Python 3.11/3.12/3.13/3.14 core compatibility is CI-gated
- [x] source distribution clean-install smoke is CI-gated
- [x] optional dependency tree is checked with pinned PyPA pip-audit before release

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

## Repository protection
- [ ] main branch ruleset enforcement is active before public publication
- [ ] main requires pull requests and passing CI before merge
- [ ] main blocks force-push and deletion

## Publication
- [ ] create `v0.1.0` tag
- [ ] create GitHub Release from `docs/RELEASE_NOTES_V0.1.md`
- [ ] attach/rebuild wheel, sdist, and checksums for the release commit
- [ ] configure an explicitly authorized PyPI publishing path
- [ ] publish `kavi-capability-compiler==0.1.0` to PyPI
- [x] do not claim production certification or universal framework support
