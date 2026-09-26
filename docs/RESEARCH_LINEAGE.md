# Research lineage

KAVI Capability Compiler is not the first capability experiment in the KAVI codebase.

Earlier public prototypes explored adjacent pieces of the problem:

- **AXIOM** explored skill discovery, composition, synthesis, sandboxing, and promotion.
- **MNEMOS** explored persistent agent memory and time-sensitive state.
- **ORACLE** explored live world-state/context injection.
- **SPECTRAFLOW** explored runtime telemetry and behavioral drift detection.

KCC deliberately narrows the product thesis.

It does not try to become a skill registry, memory system, data oracle, or general observability platform. It focuses on one question:

> What is the smallest verifiable authority this execution should possess, and why?

Ideas retained from earlier experiments:

- explicit capability inventory instead of implicit tool availability
- deterministic policy before probabilistic reasoning
- fail-closed handling for unknown authority
- fingerprints and drift detection
- bounded execution artifacts with expiry
- evidence before promotion or public claims

Ideas intentionally deferred:

- dynamic skill synthesis
- runtime sandboxing as a security guarantee
- persistent memory
- external data ingestion
- behavioral anomaly detection

These may integrate with KCC later, but only after the M1 capability benchmark validates the least-authority thesis.
