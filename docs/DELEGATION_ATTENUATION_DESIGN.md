# Delegation / Authority Attenuation Design

Status: design-only, implementation blocked  
Tracks: #71

## Objective

KCC delegation must allow a verified execution authority to produce a narrower child authority without ever widening what the parent can do.

The security invariant is:

```
effective_authority(child) ⊆ effective_authority(parent)
```

This relation must be deterministic, independently verifiable, framework-neutral, and fail closed.

No model judgment, probabilistic classifier, adapter hint, or delegation request may prove attenuation.

## Why this is a separate artifact

`kcc.capsule.v1` is a closed contract: its schema rejects additional top-level properties.

Delegation metadata such as a parent capsule identifier therefore must not be smuggled into the existing capsule contract.

The proposed design uses a separate envelope:

```
kcc.delegated-capsule.v1
```

The envelope binds:

- one exact parent capsule
- one exact child capsule
- the parent capsule ID
- a deterministic attenuation request digest
- an envelope integrity digest
- optional signature material only in a later signing-specific layer

The child remains an ordinary `kcc.capsule.v1` authority artifact. The envelope proves that this child is an attenuation of the supplied parent.

## Trust boundary

A delegation verifier MUST first verify the parent using the same trust and inventory requirements that would apply if the parent were executed directly.

A valid attenuation proof does not make an invalid, expired, drifted, forged, or untrusted parent valid.

Delegation can narrow authority. It cannot manufacture trust.

For a signed parent, signature verification remains a prerequisite.

Once a signed parent has been verified, a deterministic proof that the child is a strict subset of that parent is sufficient to preserve the parent's authority safety boundary. A separate child signature is not required merely to prove that the child has no more authority than the trusted parent: anyone holding a valid parent can at worst derive less authority.

This does **not** authenticate who performed the delegation. If an application needs authenticated delegator identity, non-repudiation, or an audit receipt for who created the child, that is a separate optional signed-delegation concern and must not be confused with authority attenuation safety.

## Source authority

Only entries in the parent `grants` set are delegable as child grants.

Parent `approvals` and `denials` MUST NOT become child grants.

A delegation request that asks to grant a capability which is not in the parent grant set fails as a whole. The system does not silently produce a partially widened or partially accepted child.

## Capability attenuation

For every child grant:

1. the capability ID MUST exist in parent grants;
2. the fingerprint MUST exactly match the parent grant fingerprint;
3. effect and risk metadata MUST be copied from the parent, not caller supplied;
4. the child inventory binding MUST remain compatible with the verified parent inventory.

The child capability set is therefore a subset of the parent grant capability set.

## Operation attenuation

Let parent operation scope be `P_ops` and child operation scope be `C_ops`.

KCC currently interprets absence of an operations constraint as unrestricted operation scope for that capability.

Safe rules:

- parent unrestricted, child unrestricted: valid
- parent unrestricted, child restricted: valid
- parent restricted, child restricted: valid only when `C_ops ⊆ P_ops`
- parent restricted, child unrestricted: invalid

Unknown or malformed operation constraints fail closed.

## Parameter-domain attenuation

For a capability, define `D(parameters)` as the set of runtime parameter mappings accepted by the current KCC Guard rules.

A child is valid only if:

```
D(child_parameters) ⊆ D(parent_parameters)
```

Absence of a parent parameter constraint means the parent accepts the unconstrained parameter mapping domain allowed by the runtime. A child may safely add validated restrictions.

If the parent has a parameter map, the child may not remove parent-required semantics or introduce a key that the parent would reject.

### Parameter key rules

When both parent and child have parameter maps:

- every child key MUST exist in the parent key set;
- every parent key with `required: true` MUST remain represented and required in the child;
- an optional parent key may be omitted by the child, which removes that parameter from child authority;
- if the parent has parameter constraints and the child omits the entire parameter map, attenuation fails because that would widen authority.

### Exact scalar

A scalar rule means exact equality.

Safe cases:

- parent scalar, child same scalar: valid
- parent scalar, child different scalar: invalid
- parent structured rule, child scalar: reject in v1; runtime scalar equality can cross structured type boundaries (`1 == True`, `1 == 1.0`), so a safe subset proof is not assumed
- parent unconstrained, child scalar: valid
- parent scalar, child structured rule: reject unless a future proof rule can establish that the structured domain is exactly a subset of the singleton parent value

### required

- parent `required: true` -> child must remain `required: true`
- parent required false/absent -> child may set true
- child may not weaken a required parent parameter

### type

A child type must denote a subset of the parent type.

Initially supported:

- same type -> valid
- parent `number`, child `integer` -> valid
- parent type absent, child supported type -> valid
- all other type changes -> invalid

Boolean is not treated as an integer or number for attenuation, matching runtime behavior.

### min / max

For numeric bounds:

- child minimum must be greater than or equal to parent minimum
- child maximum must be less than or equal to parent maximum
- adding a bound where the parent has none is valid
- removing a parent bound while keeping the parameter is invalid

### enum

- child enum must be a subset of parent enum
- adding an enum where parent has none is valid
- removing a parent enum while keeping the parameter is invalid

### max_length

- child max_length must be less than or equal to parent max_length
- adding max_length where parent has none is valid
- removing a parent max_length while keeping the parameter is invalid

### pattern

Regex implication is not generally cheap or safe to prove.

Initial rule:

- parent has no pattern, child may add any valid supported pattern
- parent has pattern, child may reuse the exact same pattern
- parent pattern replaced by a different pattern -> reject

KCC MUST NOT guess regex subset relationships.

### Combined rules

Rules are conjunctive.

For structured parent and child rules, every parent restriction must be preserved or tightened.

Structured-parent to scalar-child attenuation is rejected in v1. Merely testing the requested scalar against the parent rule is insufficient because the child scalar runtime rule accepts every value that compares equal under Python equality, which can include values the structured parent rejects. A future contract may add typed exact-value semantics if it can prove the full accepted domain.

Malformed or unsupported rules fail closed.

## Global capsule constraints

The current top-level capsule `constraints` field is not itself enforced by `authorize_call`.

Therefore it MUST NOT be treated as an authority-bearing attenuation proof until runtime semantics explicitly enforce it.

Delegation must never claim security from metadata that the Guard does not enforce.

## Time attenuation

A child must satisfy:

```
child.issued_at >= parent.issued_at
child.expires_at <= parent.expires_at
child.expires_at > child.issued_at
```

The derivation API should normally set `child.issued_at` from the current deterministic call time and clamp requested TTL to the remaining parent lifetime.

Backdating a child to gain lifetime is invalid.

An expired parent cannot produce valid delegated authority.

## Inventory and drift

The delegated envelope is valid only against the inventory context required to validate the parent.

Child capability fingerprints must match parent entries exactly.

If the parent fails inventory or fingerprint verification, the delegated artifact fails closed.

Delegation cannot be used to escape inventory drift detection by constructing a child against stale fingerprints.

## Child status

Delegation is not policy compilation.

A successful child is derived only from parent grants and therefore should be executable only for those narrowed grants.

Requests involving non-granted parent authority fail derivation rather than being converted into approval or allow states by delegation logic.

The exact child status representation must preserve existing `kcc.capsule.v1` semantics and must not imply that a new independent policy evaluation occurred.

## Provenance semantics

The delegated envelope must distinguish:

- the original parent capsule and its policy/intent provenance;
- the attenuation request;
- the derived child capsule.

The concrete provenance decision is:

1. define a canonical `kcc.delegation-request.v1` object;
2. compute `attenuation_request_digest = digest(delegation_request)`;
3. set the child capsule `intent_digest` to that attenuation-request digest;
4. inherit the parent capsule `policy_digest` into the child as **authorization provenance**, not as evidence that the policy was independently re-evaluated;
5. record that inheritance explicitly in the delegated envelope provenance block;
6. copy the parent's top-level `constraints` field unchanged because it is currently non-authoritative metadata and must not be silently reinterpreted during delegation.

A delegated child is therefore truthfully described as: "derived from this parent authority by this exact attenuation request under the parent policy provenance."

The child `task` may be supplied by the delegation request for audit/context purposes, but task text is not itself authority.

A successful child uses empty `approvals` and `denials` arrays. Delegation does not transform parent approval/deny entries into a new decision state; requests for non-granted parent authority fail derivation.

### Delegation request v1

The initial request contract should contain only security-relevant derivation inputs:

```json
{
  "version": "kcc.delegation-request.v1",
  "parent_capsule_id": "<sha256>",
  "task": "optional child task context",
  "ttl_seconds": 300,
  "capabilities": [
    {
      "id": "provider:server:tool",
      "constraints": {
        "operations": ["read"],
        "parameters": {}
      }
    }
  ]
}
```

The final schema must be closed with `additionalProperties: false`.

Effect, risk flags, fingerprints, inventory digest, policy digest, and trust material are not caller-controlled request fields. They are copied or derived from verified parent state.

## Delegated-envelope shape

The initial envelope binds the child to an externally supplied exact parent by digest rather than embedding a second full capsule:

```json
{
  "version": "kcc.delegated-capsule.v1",
  "parent_capsule_id": "<sha256>",
  "child_capsule": { "...": "kcc.capsule.v1" },
  "attenuation_request_digest": "<sha256>",
  "provenance": {
    "kind": "attenuation",
    "parent_intent_digest": "<sha256>",
    "parent_policy_digest": "<sha256>",
    "child_policy_digest_semantics": "inherited_authorization_provenance"
  },
  "fail_closed": true,
  "envelope_id": "<sha256>"
}
```

The final schema must be closed with `additionalProperties: false`.

Verification requires the exact parent capsule as an input and checks that its `capsule_id` equals `parent_capsule_id`. A caller may instead supply a verified signed-parent envelope through a signing helper, which first verifies the signature and then passes the contained parent capsule into the same core attenuation verifier.

This keeps the core zero-required-dependency contract, avoids duplicating the parent artifact inside every child envelope, and prevents a bare parent digest from being treated as sufficient evidence.

Applications that need a self-contained transport bundle may package parent + delegated envelope externally without changing the core contracts.

## Verification algorithm

A future `verify_delegated_capsule` should:

1. verify delegated-envelope integrity and version;
2. verify `fail_closed=true`;
3. require the exact parent capsule as verifier input and verify it using normal KCC verification;
4. when the parent arrives through a signed envelope, verify that signature/trust first and then use the verified contained parent capsule;
5. verify parent capsule ID binding;
6. verify child capsule integrity and ordinary capsule invariants;
7. compare child capability set to parent grants;
8. compare exact fingerprints;
9. prove operation subset for every child grant;
10. prove parameter-domain subset for every child grant;
11. prove child lifetime is within parent lifetime;
12. verify inventory/fingerprint binding;
13. reject any unsupported comparison or unknown semantic.

Only if every check passes is the delegated artifact valid.

## Adversarial test matrix

Implementation MUST begin with tests for at least:

### Capability widening
- child adds capability absent from parent grants -> reject
- child upgrades parent approval to grant -> reject
- child upgrades parent denial to grant -> reject
- child changes capability fingerprint -> reject

### Operation widening
- parent [read], child [read] -> pass
- parent [read, list], child [read] -> pass
- parent unrestricted, child [read] -> pass
- parent [read], child unrestricted -> reject
- parent [read], child [read, delete] -> reject

### Parameter widening
- tighter min/max -> pass
- looser min/max -> reject
- enum subset -> pass
- enum superset -> reject
- tighter max_length -> pass
- looser max_length -> reject
- same pattern -> pass
- different child pattern under parent pattern -> reject
- parent required true, child required false -> reject
- parent parameter map, child introduces unknown key -> reject
- parent constrained, child removes whole parameter map -> reject
- parent structured rule, child exact scalar -> reject until typed exact-value subset semantics exist
- parent structured rule, child exact scalar violating parent -> reject

### Time widening
- shorter child lifetime -> pass
- equal expiry -> pass
- expiry beyond parent -> reject
- expired parent -> reject
- child issued before parent -> reject

### Integrity / trust / drift
- tampered parent -> reject
- tampered child -> reject
- tampered envelope -> reject
- signed parent with invalid signature -> reject
- signed parent with missing trust key -> reject
- inventory drift -> reject
- fingerprint drift -> reject

### Dispatcher safety
For every rejected delegated artifact or denied child operation:

```
dispatcher_calls == 0
```

## Implementation gate

No runtime delegation API, Guard integration, signing extension, or public schema is to be merged until:

- this design is reviewed;
- parameter subset semantics are encoded as deterministic tests;
- provenance representation above is preserved without implying independent child policy evaluation;
- compatibility impact on `kcc.capsule.v1`, `kcc.sdk.v1`, and signed capsules is explicitly checked;
- authenticated delegator identity remains optional and separate from attenuation safety.

The v0.1.1 invariants remain authoritative throughout.
