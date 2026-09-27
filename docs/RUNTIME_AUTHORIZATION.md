# Runtime authorization contract

KCC `kcc.capsule.v1` capsules are deny-by-default authority artifacts.

`authorize_call(capsule, capability_id, operation, parameters)` permits a call only when:

1. capsule self-integrity is intact;
2. the capsule contract is `kcc.capsule.v1`;
3. `fail_closed` is exactly `true`;
4. the capsule has not expired;
5. the capability is present in `grants`;
6. an operation constraint, when present, contains the requested operation;
7. parameter constraints, when present, accept the supplied values.

Current parameter constraints support exact-value rules and structured rules for `required`, primitive `type`, numeric `min`/`max`, `enum`, `max_length`, and regex `pattern`.

The self-integrity digest is not an authentication mechanism. Unsigned capsules are for trusted in-process or equivalently authenticated boundaries. When compiler and executor are separated by a trust boundary, use `kcc.signed-capsule.v1` or an equivalent host-authenticated transport.

## Portable guard

`Guard` and `require_authorized_call(...)` convert denied authorization results into typed exceptions before dispatch.

- `ApprovalRequired` means the compiled authority requires a host-owned approval handoff.
- `CapabilityDenied` means policy explicitly denied the capability.
- `AuthorityDenied` covers all other authorization failures.

Every authorization exception exposes the exact decision as `.decision` and its reason as `.reason`.

`Guard.dispatch_sync(...)`, `Guard.dispatch(...)`, and the lower-level `guarded_dispatch(...)` follow the same boundary:

1. evaluate authorization;
2. if denied or approval-required, do not call the supplied dispatcher;
3. if allowed, pass the exact authorized parameter mapping to the dispatcher;
4. support synchronous and asynchronous host dispatchers;
5. propagate host execution failures without reinterpreting them as authority decisions.

## Fail-closed behavior

Approval entries are not executable grants. Unsupported capsule versions, missing `fail_closed=true`, malformed capsule structures, expired capsules, explicit denials, absent grants, operation mismatches, and parameter mismatches are rejected before host dispatch.

KCC does not authenticate application users, provide IAM/KMS/secrets management, sandbox the underlying tool, or evaluate arbitrary JSON Schema predicates at runtime. Those remain host responsibilities.

See `SDK_COMPATIBILITY.md` for the v0.1 compatibility boundary.
