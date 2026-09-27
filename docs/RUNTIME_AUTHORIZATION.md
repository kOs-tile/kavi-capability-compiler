# Runtime authorization contract

KCC `kcc.capsule.v1` capsules are deny-by-default authority artifacts.

`authorize_call(capsule, capability_id, operation, parameters)` permits a call only when:

1. capsule self-integrity is intact;
2. the capsule contract is `kcc.capsule.v1`;
3. `fail_closed` is exactly `true`;
4. the capsule has not expired;
5. the capability is present in `grants`;
6. an operation constraint, when present, contains the requested operation;
7. parameter constraints, when present, accept the supplied values;
8. when a current inventory is bound, that inventory still matches the capsule's compiled authority surface.

Current parameter constraints support exact-value rules and structured rules for `required`, primitive `type`, numeric `min`/`max`, `enum`, `max_length`, and regex `pattern`. Structured rule objects are validated at compile time: unknown rule keys and malformed rule values are rejected rather than silently ignored.

When a capsule includes a `parameters` constraint object, its keys are also an allowlist. A runtime parameter that is not named in that object is rejected with `parameter_not_granted:<name>`. Use an empty rule object (`{}`) to explicitly permit a parameter without narrowing its value.

The self-integrity digest is not an authentication mechanism. Unsigned capsules are for trusted in-process or equivalently authenticated boundaries. When compiler and executor are separated by a trust boundary, use `kcc.signed-capsule.v1` or an equivalent host-authenticated transport.

## Inventory-bound Guard

The recommended embedded form is:

```python
guard = kcc.Guard.from_capsule(capsule, inventory=current_inventory)
```

The bound inventory is rechecked before every authorization decision. If its semantic digest or a granted capability fingerprint no longer matches the compiled capsule, authorization fails before dispatch. This catches stale capsules after capability additions, removals, and schema/authority changes.

If the host's registry can mutate during a long-running execution, the host should create a new Guard from a fresh inventory at the boundary where that mutation can occur.

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

Approval entries are not executable grants. Unsupported capsule versions, missing `fail_closed=true`, malformed capsule structures, invalid bound-inventory integrity, inventory drift, expired capsules, explicit denials, absent grants, operation mismatches, undeclared parameter keys, unsupported/malformed parameter rules, and parameter mismatches are rejected before host dispatch. Runtime values that cannot be evaluated against numeric or length bounds fail closed with `parameter_type_mismatch:<name>` rather than escaping the Guard as a comparison error.

KCC does not authenticate application users, provide IAM/KMS/secrets management, sandbox the underlying tool, or evaluate arbitrary JSON Schema predicates at runtime. Those remain host responsibilities.

See `SDK_COMPATIBILITY.md` for the v0.1 compatibility boundary.
