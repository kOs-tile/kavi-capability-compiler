# Dispatch-time current authority — v0.2

Status: unreleased v0.2 development contract.

KCC capsules are bounded authority artifacts, not a revocation service. Integrity,
expiry, inventory binding, operation scope, and parameter scope do not by
themselves prove that the host still considers the authority live.

A host may revoke or reassign authority after capsule compilation without
mutating the capsule. Examples include:

- approval withdrawn
- task reassigned to another worker
- grant revoked
- worker/session invalidated by a control plane

## Guard contract

v0.2 adds an optional host-supplied `current_authority_resolver` to `Guard`.

The order is:

```
capsule / signature / inventory / call-scope checks
        -> must already be allowed
host current-authority resolver
        -> may preserve or reduce authority
        -> can never widen a capsule denial
dispatcher
```

Example:

```python
authority = {"active": True}

def current_authority(context):
    return {
        "active": authority["active"],
        "reason": "active" if authority["active"] else "task_reassigned",
    }

guard = kcc.Guard.from_capsule(
    capsule,
    inventory=inventory,
    current_authority_resolver=current_authority,
)
```

The resolver receives a host-local context containing:

- `capsule_id`
- capsule `task`
- `capability_id`
- `operation`
- exact `parameters`
- caller-supplied `now`

The resolver contract is intentionally small:

```python
{"active": True, "reason": "active"}
{"active": False, "reason": "authority_revoked"}
```

Only a real boolean `active` field is accepted.

## Fail-closed behavior

When a resolver is configured:

- `active=False` -> `current_authority_revoked`
- missing/malformed/unknown `active` -> `current_authority_unknown`
- resolver exception -> `current_authority_resolver_error`
- async resolver used from sync Guard dispatch -> `current_authority_resolver_async_unsupported`
- async Guard dispatch may use either a sync or async resolver

All resolver denials happen before host dispatcher invocation.

The resolver is called only after capsule authority already allows the call.
Therefore an `active=True` resolver response cannot turn an ungranted,
approval-required, denied, expired, tampered, or out-of-scope call into allow.

## Host ownership

KCC does not own the revocation/current-authority store.

The resolver may consult host-owned state such as:

- assignment generation / authority epoch
- approval record
- worker lease
- session state
- revocation registry
- control-plane task ownership

KCC core does not require a hosted service, database, network client, or
framework-specific dependency.

## Compatibility boundary

If no `current_authority_resolver` is configured, Guard retains the existing
capsule model: authority remains usable until another fail-closed check rejects
it, including expiry, integrity failure, inventory drift, signature failure, or
call-scope denial.

Applications that require immediate revocation or reassignment semantics must
configure a current-authority resolver. Short TTL remains useful defense in
depth, but is not a substitute for revocation when immediate invalidation is a
requirement.

The host should place Guard immediately before the actual side-effect
dispatcher. If the host authorizes now but delays the side effect inside another
queue/system, that later execution boundary needs its own current-authority
check.
