# Security Policy

KAVI Capability Compiler is security-sensitive alpha software.

## Reporting a vulnerability

Please do not open a public issue for a vulnerability that could expose credentials, bypass a capsule boundary, incorrectly authorize a denied capability, forge a signed capsule, or leak secret configuration.

Use GitHub's private security advisory / vulnerability reporting flow for this repository when available.

For non-sensitive correctness bugs, normal GitHub issues are appropriate.

## Security invariants

Changes must preserve these properties:

- unknown authority never becomes silent authority
- denied calls do not reach the host dispatcher
- approval-required authority is not treated as granted
- provenance alone does not create semantic authority
- signed envelopes cannot self-declare trusted keys
- secret values do not enter discovery/config artifacts
- external evidence cannot expand a compiled capsule

## Scope

KCC does not replace:

- application identity and authentication
- IAM
- secret storage
- KMS
- host sandboxing
- network controls
- dependency security
- human approval systems

A valid KCC capsule means the request fits the authority KCC compiled under its current model. It is not a certification that the underlying tool or application is safe.

## MCP transport boundary

Remote Streamable HTTP discovery requires HTTPS.

Plaintext `http://` discovery is accepted only for loopback hosts such as
`localhost`, `127.0.0.1`, and `::1`, where it is useful for local development
and test fixtures. KCC rejects remote plaintext HTTP before opening a connection.

KCC also rejects URL userinfo credentials such as
`https://user:password@example.com/...`. Supply authentication through the
host-owned header configuration instead. Header values remain in memory for the
request and are not copied into discovery artifacts.

These controls reduce credential exposure and prevent a remote plaintext
network path from silently modifying the capability surface returned by
`tools/list`.

## CI and release supply chain

Repository workflows pin external GitHub Actions to full immutable commit SHAs.
CI contains a regression check that rejects mutable action references.

Release reproducibility tooling is version-pinned. Publication credentials must
not be stored in the repository; the preferred publication path is short-lived
OIDC / trusted publishing with build and publish permissions separated.

## Artifact integrity at compile time

KCC treats capability manifests, inventories, and inventory locks as
security-sensitive authority artifacts.

Before compilation, KCC validates the inventory's deterministic identity,
fingerprints, derived effect analysis, and digest. Manifest scanning validates
the manifest digest rather than silently rebuilding authority from a stale or
tampered envelope. Inventory-lock diffing validates the lock digest and rejects
duplicate canonical capability identities.

These are integrity checks, not authentication. A hostile party that is allowed
to replace an entire unsigned artifact and recompute all of its self-integrity
fields is already across the artifact trust boundary. Cross-process trust must
therefore use host authentication and, where applicable, KCC signed capsules.

CI also audits the currently resolved optional runtime dependency set against
the Python Packaging Authority vulnerability audit database before release.

Git checkout steps disable credential persistence after checkout. The CI token is
read-only and is not left configured in the repository working tree.

The optional signing dependency requires a vulnerability-audited
`cryptography>=50.0.1,<51` release line; older vulnerable release lines are
not accepted by the signing extra.

## Publication trust boundary

The production release workflow separates build, PyPI publication, registry
verification, and GitHub Release creation into distinct jobs.

The artifact is built once from an exact 40-character commit SHA, then moved
between jobs through GitHub Actions artifacts. Publication jobs do not rebuild
the package.

PyPI publication requires a protected GitHub Environment named `pypi` and
uses Trusted Publishing/OIDC. No long-lived PyPI credential is stored. The PyPI
job receives `id-token: write` but not repository write authority. The GitHub
Release job receives `contents: write` but no OIDC permission. Both jobs are
gated by the protected environment.

Before first publication, the workflow fails closed if the PyPI project name is
already registered, if the intended Git tag already exists, if the requested
release SHA is not the current `main` head, or if any artifact checksum differs
from the verified build payload.
