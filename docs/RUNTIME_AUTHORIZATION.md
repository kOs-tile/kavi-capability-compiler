# Runtime authorization contract

KCC capsules are deny-by-default authority artifacts.

`authorize_call(capsule, capability_id, operation, parameters)` permits a call only when:

1. capsule integrity is intact;
2. capsule has not expired;
3. the capability is present in `grants`;
4. an operation constraint, when present, contains the requested operation;
5. parameter constraints, when present, accept the supplied values.

Current parameter constraints support exact-value rules and structured rules for `required`, primitive `type`, numeric `min`/`max`, `enum`, `max_length`, and regex `pattern`.

This is deliberately a small enforcement primitive, not a hosted gateway. Adapters can invoke it before dispatching to MCP or another tool runtime.

## Portable guard

`require_authorized_call(...)` converts a denied authorization result into an
`AuthorityDenied` exception before dispatch.

`guarded_dispatch(...)` is a small framework-agnostic reference adapter:

1. evaluate `authorize_call()`;
2. if denied, do not call the supplied dispatcher;
3. if allowed, pass the exact authorized parameter mapping to the dispatcher;
4. support sync or async dispatchers;
5. propagate execution failures without reinterpreting them as authority decisions.

This is an integration primitive for bounded dogfood, not a hosted transport or
a claim that arbitrary MCP runtimes are already mediated.

## Fail-closed behavior

Approval entries are not executable grants. Denied, absent, expired, operation-mismatched, and parameter-mismatched calls are rejected.

The v0 primitive does not yet authenticate the caller, sign capsules, validate arbitrary JSON Schema predicates, or mediate network transport. Those remain outside the M1 claim.
