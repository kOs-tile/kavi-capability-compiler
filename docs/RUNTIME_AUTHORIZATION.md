# Runtime authorization contract

KCC capsules are deny-by-default authority artifacts.

`authorize_call(capsule, capability_id, operation, parameters)` permits a call only when:

1. capsule integrity is intact;
2. capsule has not expired;
3. the capability is present in `grants`;
4. an operation constraint, when present, contains the requested operation;
5. parameter constraints, when present, accept the supplied values.

Current parameter constraints support exact values and numeric `min`/`max` plus `enum` membership.

This is deliberately a small enforcement primitive, not a hosted gateway. Adapters can invoke it before dispatching to MCP or another tool runtime.

## Fail-closed behavior

Approval entries are not executable grants. Denied, absent, expired, operation-mismatched, and parameter-mismatched calls are rejected.

The v0 primitive does not yet authenticate the caller, sign capsules, validate arbitrary JSON Schema predicates, or mediate network transport. Those remain outside the M1 claim.
