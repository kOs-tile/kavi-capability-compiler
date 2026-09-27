# SDK and Contract Compatibility

KAVI Capability Compiler v0.1.0 exposes a framework-neutral Python SDK identified by `kcc.sdk.v1`.

## Versioned data contracts

The v0.1 release candidate freezes these contracts:

- `kcc.capabilities.v1` — normalized capability manifest
- `kcc.inventory.v1` — analyzed capability inventory
- `kcc.inventory-lock.v1` — deterministic authority lock
- `kcc.capsule.v1` — task-scoped execution capsule
- `kcc.signed-capsule.v1` — Ed25519 envelope over one exact capsule
- `kcc.sdk.v1` — public Python SDK surface and exception semantics

A breaking field, meaning, trust, or authorization change requires a new contract version. KCC may make fail-closed bug fixes inside a contract version when the previous behavior could authorize more authority than intended.

## Python SDK compatibility

For the `0.1.x` line:

- names in `kavi_capability_compiler.__all__` remain available
- framework-specific names are not added to the public core API
- the core install remains usable without optional MCP or signing dependencies
- a denied or approval-required call never reaches the caller-supplied dispatcher
- unknown or unsupported authority is rejected or routed to approval; it is never silently granted

## Exception semantics

`AuthorityDenied` is the base runtime authorization exception.

Every KCC authorization exception:

- stores the exact authorization decision in `.decision`
- exposes the decision reason in `.reason`
- uses the reason as its exception message
- is raised before the host dispatcher is invoked

`ApprovalRequired` is raised only when the decision reason is `approval_required`.

`CapabilityDenied` is raised only when policy explicitly places the requested capability in the capsule's denial set and the reason is `capability_denied`.

All other authorization failures, including invalid integrity, unsupported capsule version, missing fail-closed marker, expiry, missing grants, operation violations, and parameter violations, raise `AuthorityDenied`.

Dispatcher exceptions are not converted into authorization exceptions after a call has been authorized.

## Signed capsules

`kcc.signed-capsule.v1` can contain only `kcc.capsule.v1`.

Signing refuses a capsule that:

- has invalid capsule integrity
- uses an unsupported capsule contract version
- does not set `fail_closed` to true

Verification binds trust to host-supplied public keys. The envelope's `key_id` identifies a key but cannot make that key trusted.

## Compatibility boundary

KCC does not claim compatibility guarantees for private module names, benchmark fixtures, repository-only case studies, or unexported implementation helpers.

External runtimes should integrate through the public SDK and versioned JSON contracts rather than importing internal modules.
