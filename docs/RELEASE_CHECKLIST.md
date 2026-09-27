# v0.1 Release Checklist

## Code
- [x] main contains the M0–M4 shipped implementation
- [x] package version and `__version__` both equal 0.1.0
- [x] public `__all__` contract passes
- [x] full test suite passes — 84 tests at final RC checkpoint
- [x] all benchmark safety gates pass

## Packaging
- [x] wheel builds
- [x] sdist builds
- [x] wheel installs with `--no-deps`
- [x] core SDK imports from the installed wheel
- [x] core CLI works from the installed wheel
- [x] public JSON schemas load from the installed wheel
- [x] KAVI/Hermes/Codex-specific runtime modules are absent from the installed core wheel
- [x] `mcp` extra installs independently
- [x] `signing` extra installs independently
- [x] Apache-2.0 license metadata/file and Python >=3.11 are declared
- [x] artifact SHA-256 checksums are generated during release CI

## Documentation
- [x] README describes v0.1 behavior
- [x] embedded SDK guide is current
- [x] universal manifest guide is current
- [x] framework-neutral execution-evidence contract is current
- [x] benchmark report includes limitations
- [x] integration examples execute in CI
- [x] framework-specific validation targets are separated from the installed core

## Publication
- [ ] create `v0.1.0` tag
- [ ] create GitHub Release from `docs/RELEASE_NOTES_V0.1.md`
- [ ] attach/rebuild wheel, sdist, and checksums for the release commit
- [ ] configure an explicitly authorized PyPI publishing path
- [ ] publish `kavi-capability-compiler==0.1.0` to PyPI
- [x] do not claim production certification or universal framework support
