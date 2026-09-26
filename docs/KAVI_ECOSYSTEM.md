# KAVI engineering ecosystem

KAVI Capability Compiler (KCC) is the authority plane, not a monolith for every agent concern.

The surrounding public research repositories are intentionally being narrowed into orthogonal subsystems. This document distinguishes **implemented interoperability** from intended architecture so repository boundaries are not mistaken for an already-deployed integrated platform.

## System boundaries

| Repository | Role | Relationship to KCC | Current contract status |
|---|---|---|---|
| `kavi-capability-compiler` | least-authority compiler + call authorization primitive | authority plane | implemented, benchmarked in M1 |
| `axiom` | skill discovery / synthesis / evaluation foundry | capability producer | **implemented adapter**: promoted skills export an MCP-shaped snapshot for KCC scanning |
| `mnemos` | provenance-aware persistent memory | state/memory plane | admission audit implemented; can be referenced by execution evidence digest |
| `oracle` | provenance-aware current-world context ingestion | evidence/context plane | evidence ledger + canonical digest implemented; digest can be bound to execution evidence |
| `spectraflow` | behavior + authority-drift observability | observability plane | KCC correlation + observational authority-drift evaluator implemented |
| `phantom` | provider-agnostic browser extraction verification | tool/data plane | extraction contracts + drift reports + evidence fingerprints implemented |
| `nephilim` | evidence-first on-chain pattern detection lab | domain research/data plane | detector evidence artifact + normalized input fingerprint implemented; never trading authority |
| `taxflow-crm` | vertical SaaS portfolio/demo | application demo | intentionally outside the KCC core path |

## Implemented handoff: AXIOM -> KCC

AXIOM now exports promoted skills through `axiom.integrations.kcc.export_kcc_snapshot(...)`.

The adapter deliberately does **not** claim `readOnlyHint`, destructive safety, or any other authority annotation merely because a skill passed AXIOM evaluation. KCC receives the skill as observed capability evidence, fingerprints it, classifies the side effect, audits ambiguity, and decides whether a task-scoped capsule can grant it.

```text
AXIOM candidate skill
    |
    v
AXIOM security/evaluation gates
    | only promoted ACTIVE skills
    v
MCP-shaped observed snapshot
    | no inferred authority hints
    v
KCC scan -> classify -> audit -> compile
    |
    v
bounded execution capsule -> authorize_call()
```

## Non-authority evidence rule

Outputs from ORACLE, MNEMOS, SPECTRAFLOW, PHANTOM, or NEPHILIM may inform an agent or a verifier, but they do not grant execution authority.

Examples:

- ORACLE saying a value is `REAL` means its data provenance is real, not that an agent may trade on it.
- MNEMOS retrieving a remembered instruction does not elevate that instruction above current policy.
- SPECTRAFLOW detecting drift may trigger review, but it does not mutate a KCC capsule.
- PHANTOM successfully extracting a page does not authorize a later browser write action.
- NEPHILIM detecting a sandwich pattern does not authorize a transaction.

That separation is intentional: evidence can affect planning and approval decisions without silently expanding capability.

## Next integration gates

Before another direct integration is added, it should satisfy all of the following:

1. The producer exposes deterministic provenance/fingerprints for the artifact being handed off.
2. KCC receives observed capability evidence, not a producer-authored permission decision.
3. Unknown or mixed side effects remain approval-required or denied unless operation constraints resolve them.
4. Drift between observed capability and compiled capsule is detectable.
5. The integration has a regression test and CI evidence in both the producer contract and KCC-facing fixture/harness.

These are target gates, not claims that every subsystem already meets them.


## Execution evidence envelope

KCC now provides a non-authority `kavi.execution-evidence.v0` envelope that binds
external subsystem artifact digests to one execution and one capsule. See
[`EXECUTION_EVIDENCE.md`](EXECUTION_EVIDENCE.md).

This is an audit contract, not a permission contract. The envelope always states
`authority_granted=false`; only the bound KCC capsule and runtime authorization
primitive define execution authority.
