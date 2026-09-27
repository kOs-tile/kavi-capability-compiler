# v0.1 Release Checklist

## Code
- [ ] main contains the M0–M4 shipped implementation
- [ ] package version and `__version__` both equal 0.1.0
- [ ] public `__all__` contract passes
- [ ] full test suite passes
- [ ] all benchmark safety gates pass

## Packaging
- [ ] wheel builds
- [ ] sdist builds
- [ ] wheel installs with `--no-deps`
- [ ] core SDK imports from the installed wheel
- [ ] core CLI works from the installed wheel
- [ ] `mcp` extra installs independently
- [ ] `signing` extra installs independently
- [ ] package metadata reports Apache-2.0 and Python >=3.11
- [ ] artifact SHA-256 checksums generated

## Documentation
- [ ] README describes v0.1 behavior
- [ ] embedded SDK guide is current
- [ ] universal manifest guide is current
- [ ] benchmark report includes limitations
- [ ] integration examples execute in CI
- [ ] no Hermes/KAVI/Codex dependency is implied

## Release
- [ ] create release candidate tag only after branch CI is green
- [ ] attach wheel, sdist, and checksums if publishing a GitHub release
- [ ] PyPI publication requires an explicitly authorized publishing credential
- [ ] do not claim production certification or universal framework support
