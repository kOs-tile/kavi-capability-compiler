# KCC Capability Benchmark v0.1

This benchmark exists to falsify the product thesis, not market it.

## Primary safety metric

**False-safe rate:** fraction of dangerous capabilities classified as safe/read.

Overall accuracy is secondary. Unknown is preferable to false-safe because KCC can fail closed on unknown authority.

## Expansion plan

The seed corpus only validates the harness. M1 is not complete until the corpus contains heterogeneous real MCP tool surfaces, adversarial cases, drift scenarios, and task intents.

Target: 300–500 labeled tools from at least 30 MCP servers/snapshots.

## Comparators

- static standing permissions
- per-call probabilistic gating (Jev-style)
- KCC precompiled authority
- KCC + probabilistic gating for ambiguous in-capsule calls
