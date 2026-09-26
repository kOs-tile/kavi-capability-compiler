# KAVI execution stack boundaries

KAVI Capability Compiler remains intentionally narrow. The surrounding KAVI
research repositories may integrate with it, but none of them are dependencies
of the compiler kernel or the M1 benchmark.

## Responsibility graph

```
external web / APIs / chains
        |
        v
PHANTOM --------> extraction contract evidence
ORACLE ---------> provenance + freshness + actionability
        |
        v
AXIOM ----------> candidate skills / minimal capability plan
        |
        v
KCC ------------> audited task-scoped authority capsule
        |
        v
Hermes ----------> execution
        |
        +--------> SPECTRAFLOW runtime telemetry / drift evidence
        |
        +--------> MNEMOS accepted persistent memory
```

## Boundaries

### KCC — authority compiler

Owns:
- observed capability inventory
- side-effect/effective-authority classification
- policy evaluation
- task-scoped execution capsules
- fingerprints, expiry, drift and integrity verification

Does not own:
- skill generation
- external data truth
- browser automation
- persistent memory
- runtime anomaly detection

### AXIOM — capability planner / skill foundry

AXIOM may discover, compose, or synthesize candidate executable skills.

A sandbox pass is **code evidence, not authority**. By default a synthesized
skill stops at `READY_FOR_AUTHORIZATION`. AXIOM may emit a minimal
KCC authorization bundle, but `authorization.granted=false` until KCC compiles
an execution capsule.

### ORACLE — evidence-aware world state

ORACLE may provide external facts to an agent only with machine-readable
provenance, source state, age, confidence, and actionability. Simulated or stale
data must not silently become an actionable KCC task assumption.

KCC does not certify that ORACLE data is true; it can only bind the authority
for an execution that consumes that evidence.

### PHANTOM — browser extraction reliability

PHANTOM's active wedge is not browser stealth. It defines deterministic
extraction contracts, canonical fingerprints, and replay/drift evidence over
structured browser outputs. The validator is provider-independent.

PHANTOM proves whether an extraction matched its declared contract; it does not
prove the underlying website statement is objectively true.

### SPECTRAFLOW — runtime observability

SPECTRAFLOW observes model/proxy behavior and semantic drift after execution.
It can produce evidence for incident response or future policy changes, but it
does not grant or expand KCC authority.

### MNEMOS — persistent memory

MNEMOS stores and decays accepted memory. Memory retrieval must not implicitly
expand execution authority. A future integration should preserve source and
freshness metadata so remembered claims do not become silent authority or
silent truth.

## Domain research

NEPHILIM is a domain-specific on-chain detection lab. It can feed ORACLE-style
evidence if its detector outputs are validated, but it is not part of the KCC
critical path.

TaxFlow CRM is an application/portfolio vertical and is intentionally outside
the agent infrastructure stack.

## M1 rule

The KCC M1 capability benchmark remains the flagship validation gate. These
integrations may evolve in parallel, but they must not widen the KCC kernel
until the least-authority thesis passes its benchmark.
