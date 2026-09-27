# Publishing v0.1.0

Publication is intentionally separated from ordinary CI.

## One-time trust setup

Before a real upload, configure a PyPI pending Trusted Publisher with exactly:

- PyPI project name: `kavi-capability-compiler`
- GitHub owner: `kOs-tile`
- repository: `kavi-capability-compiler`
- workflow: `release.yml`
- environment: `pypi`

Then configure the GitHub `pypi` environment so a trusted maintainer must approve the publish job.

Do not create or store a PyPI API token for this release.

## Dry run

Run the GitHub Actions workflow `release-v0.1.0` from the `main` branch with:

- `publish=false`
- `confirm_version=v0.1.0`

The workflow will rebuild wheel and sdist twice, canonicalize sdist metadata, require bit-for-bit equality, verify the wheel surface, run Twine metadata checks, clean-install the wheel, generate SHA-256 checksums, and upload the verified artifacts only to the GitHub Actions run.

No PyPI upload, tag, or GitHub Release occurs in dry-run mode.

## Real publication

After the dry run is reviewed, run the same workflow from `main` with:

- `publish=true`
- `confirm_version=v0.1.0`

The build job still has read-only permissions. The PyPI job receives only `contents: read` plus `id-token: write`, and only behind the `pypi` environment. PyPI Trusted Publishing exchanges that OIDC identity for short-lived upload credentials.

Only after PyPI upload succeeds does the final job receive `contents: write` and create tag/release `v0.1.0` at the exact workflow commit, attaching the same wheel, sdist, and `SHA256SUMS`.

The workflow refuses to overwrite an existing `v0.1.0` GitHub Release.

## Failure semantics

- build/preflight failure: nothing is published
- PyPI environment approval denied: nothing is published
- PyPI upload failure: GitHub Release job does not run
- GitHub Release failure after successful PyPI upload: do not rebuild or re-upload PyPI; repair only the GitHub Release from the exact verified commit/artifacts
