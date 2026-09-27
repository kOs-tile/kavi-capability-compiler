# External Diagnostics Dogfood

This validation measures the public v0.1.0 SDK's fail-closed diagnostic contract from an external consumer environment.

It installs the published package rather than repository source and imports only the public `kavi_capability_compiler` API.

## Distribution paths

The same diagnostic cohort runs against:

- the GitHub Pages Simple Repository index
- the direct GitHub Release wheel

Python 3.11 is used here because Python 3.11-3.14 public package installation and core SDK behavior are already separately covered by the external-consumer matrix.

## Scenarios

Each distribution path intentionally triggers:

1. capability not granted
2. explicit policy denial
3. approval required
4. operation not granted
5. unexpected parameter key
6. required parameter missing
7. parameter type mismatch
8. expired capsule
9. current-inventory drift
10. tampered capsule integrity

## Required diagnostics contract

Every scenario must prove:

- denial occurs before dispatcher invocation
- the documented public exception class is raised
- `.reason` is deterministic and machine-readable
- the exception message equals `.reason`
- `.decision` preserves structured authorization data
- verification-based failures expose the failed verification check names

This produces evidence about debuggability without weakening fail-closed behavior.

## Limits

This is a diagnostic-contract probe, not a security certification.

It does not test every parameter rule, signing failure, transport error, or host-responsibility boundary. Those remain covered by their dedicated regression/security suites where applicable.

No model calls, paid APIs, vendor credentials, or private KCC modules are used.
