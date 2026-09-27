# External Consumer Dogfood

This validation treats the published KCC package as an external consumer would.

It does not install the repository source and does not call a model, vendor API, or paid service.

## Distribution paths

The cohort installs exactly `kavi-capability-compiler==0.1.0` through:

1. the GitHub Pages Simple Repository:
   `https://kos-tile.github.io/kavi-capability-compiler/simple/`
2. the direct GitHub Release wheel URL.

Each path is exercised on CPython 3.11, 3.12, 3.13, and 3.14 for eight clean-install cells.

## Consumer boundary

Before installation, the workflow changes to `/tmp`, clears `PYTHONPATH`, and proves that `kavi_capability_compiler` cannot be imported.

After public installation, the smoke runs from a temporary directory with an empty `PYTHONPATH`. It also requires the imported package path to resolve from `site-packages`.

This prevents the checkout from accidentally satisfying the test.

## Per-cell checks

Every cell verifies:

- package metadata version `0.1.0`
- public `__version__ == 0.1.0`
- `SDK_VERSION == kcc.sdk.v1`
- CLI `kcc --version`
- all five packaged public schemas
- Generic JSON adapter
- OpenAI-shaped adapter
- Anthropic-shaped adapter
- MCP-shaped adapter
- OpenAPI adapter
- inventory-bound Guard construction
- one granted read dispatch reaches the host dispatcher exactly once
- an out-of-capsule mutation raises `AuthorityDenied`
- the denied mutation reaches the dispatcher zero times

The workflow writes one JSON evidence file per cell and a combined cohort artifact only if all eight cells pass.

## Limits

This is distribution and embedded-SDK interoperability evidence, not a security certification and not a substitute for the adversarial/security benchmark suite.

The GitHub Pages index intentionally hosts KCC's own artifacts only. The default KCC core has zero required third-party runtime dependencies, so core installation is self-contained through that index. Optional extras that require third-party packages are outside this Simple-Index cohort; they should use an installation path that can resolve their external dependencies.

The workflow is not scheduled. It runs manually or when its own dogfood workflow/script/documentation changes, avoiding recurring CI cost and noise until external evidence justifies a broader cadence.
