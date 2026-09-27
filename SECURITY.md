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

## Release security gates

Before a public release:

- public capsule verification validates supplied inventory integrity;
- inventory drift checks validate both lock and current-inventory integrity;
- authenticated non-loopback MCP HTTP discovery requires HTTPS;
- URL userinfo credentials are rejected for Streamable HTTP discovery;
- GitHub Actions used by CI are pinned to immutable commit SHAs;
- checkout credentials are not persisted in the test workspace;
- release build/check tooling is version-pinned;
- release CI scans tracked source for obvious private-key/token material and rejects mutable workflow action refs;
- release artifacts must still pass reproducibility, wheel-surface, metadata, and clean-install gates.

Self-integrity digests are tamper-evidence inside the documented trust boundary; they are not authentication. Signed capsules or equivalent authenticated transport remain required across untrusted boundaries.

Security-sensitive optional dependency floors are set above known affected ranges at release time. The v0.1 preflight requires `httpx2>=2.12.0,<3` and `cryptography>=50.0.1,<51`; future releases must re-check current advisories rather than treating these floors as permanently sufficient.
