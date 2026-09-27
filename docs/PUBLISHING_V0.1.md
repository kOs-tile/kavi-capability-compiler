# v0.1.0 Publication

KCC publishes with PyPI Trusted Publishing. No long-lived PyPI API token is stored in GitHub.

## Required one-time setup

Create a PyPI pending Trusted Publisher with exactly:

- project: `kavi-capability-compiler`
- owner: `kOs-tile`
- repository: `kavi-capability-compiler`
- workflow: `release.yml`
- environment: `pypi`

Configure the GitHub environment named `pypi` with a trusted manual reviewer before the first real publication.

## Dry run

From GitHub Actions, run the `release` workflow on `main` with:

- `target_sha`: the exact current green `main` SHA
- `publish=false`
- `confirm_version`: may remain empty

The workflow checks out that exact SHA, validates metadata and action pins, builds wheel and sdist twice, canonicalizes sdist archive metadata, requires bit-for-bit equality, runs Twine checks, generates SHA-256 checksums, clean-installs the wheel, and uploads only a short-lived Actions artifact.

No tag, GitHub Release, PyPI upload, OIDC grant, or repository write permission is used in dry-run mode.

## Real publication

Run the same workflow on `main` with:

- `target_sha`: the exact current green `main` SHA
- `publish=true`
- `confirm_version=v0.1.0`

Before building, KCC requires the target to equal the workflow's own `main` SHA and requires an already-successful `test` workflow from a `main` push for that SHA. Existing `v0.1.0` tag/release state is rejected.

The verified artifact set is then passed to a separate PyPI job. Only that job has `id-token: write`, and it is protected by the `pypi` environment. PyPI exchanges the GitHub OIDC identity for short-lived credentials.

Only after PyPI publication succeeds does a separate job receive `contents: write` and create GitHub tag/release `v0.1.0` at the exact target SHA, attaching the same wheel, sdist, and `SHA256SUMS`.

## Failure behavior

- verification/build failure: nothing published
- missing/denied environment approval: nothing published
- PyPI failure: GitHub tag/release job does not run
- GitHub Release failure after PyPI success: do not rebuild or republish the immutable PyPI version; repair only the GitHub release against the exact verified SHA/artifacts
