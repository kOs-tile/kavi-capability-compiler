# v0.1.0 Distribution

KCC v0.1.0 is published through GitHub Release. PyPI is not a release prerequisite.

## Canonical v0.1.0 artifacts

The GitHub Release contains:

- one universal Python wheel
- one source distribution
- `SHA256SUMS`

The release workflow builds the wheel and sdist twice from the exact green `main` commit, canonicalizes sdist archive metadata to the commit epoch, requires bit-for-bit equality, validates metadata with Twine, checks the installed wheel surface, performs a clean no-dependency install, and verifies the generated Simple Repository index before publication.

The release job re-verifies `SHA256SUMS` before creating tag/release `v0.1.0`.

## Direct installation

```bash
python -m pip install https://github.com/kOs-tile/kavi-capability-compiler/releases/download/v0.1.0/kavi_capability_compiler-0.1.0-py3-none-any.whl
```

This URL points to the versioned `v0.1.0` release asset rather than a mutable branch.

## Simple Repository index

KCC includes a generator for the Python Simple Repository API. The generated project page links directly to the immutable GitHub Release assets and includes each artifact's SHA-256 digest in the URL fragment.

After GitHub Pages is enabled with GitHub Actions as the publishing source, run the manual `deploy-simple-index` workflow. That workflow:

1. downloads only the fixed `v0.1.0` release assets,
2. verifies `SHA256SUMS`,
3. regenerates the static Simple Repository pages,
4. validates the file URLs, hashes, and Requires-Python marker,
5. deploys only the generated static site.

Installation through the index then becomes:

```bash
python -m pip install --index-url https://kos-tile.github.io/kavi-capability-compiler/simple/ kavi-capability-compiler
```

A Pages deployment failure does not modify or invalidate the GitHub Release.

## Future PyPI mirror

When PyPI account registration becomes available, publish the exact already-released v0.1.0 wheel and source distribution. Do not rebuild v0.1.0.

Before mirroring, verify the files against the GitHub Release `SHA256SUMS`. PyPI is a distribution mirror, not the authority source for the original v0.1.0 build.


## Published verification record

- release tag: `v0.1.0`
- release commit: `63bd0e228f2587c55e246051afdbf2d8b46086a3`
- wheel SHA-256: `2a17d42c38317d8df324bea392882564bc53d568ae83cc0a042476a06f0f872e`
- sdist SHA-256: `acd7842ca43794b0d488a49558b962422de120c89936d9575cacec4ec6972fa7`
- `SHA256SUMS` SHA-256: `31626e4272b04c93b46d5ed3c315f8a81f7d8a3f09f4c54ff590ccad264a3548`

The public GitHub Release API reports the current release as `immutable=false`. The tag SHA and asset digests above are verified, but GitHub's platform-level Immutable Releases enforcement is not being claimed for v0.1.0. Enable repository Immutable Releases protection before the next release cycle.
