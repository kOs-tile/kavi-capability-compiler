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
