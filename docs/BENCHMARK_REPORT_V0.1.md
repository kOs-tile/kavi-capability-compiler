# KCC v0.1 Benchmark Report

This report summarizes the evidence used for the v0.1 release candidate.

## Capability classification development corpus

- 487 sourced capabilities
- 30 MCP surfaces
- 173 labeled dangerous samples
- accuracy at recorded M1 checkpoint: 89.73%
- dangerous recall: 100%
- observed false-safe outcomes: 0
- unknown rate: 11.91%
- overblocking rate: 3.50%

This is a development corpus and must not be treated as an independent production estimate.

## Sealed post-freeze classification holdout

First reveal:
- 63 previously unseen capabilities
- 2 new surfaces
- 27 dangerous samples
- accuracy: 80.95%
- dangerous recall: 100%
- false-safe: 0
- unknown rate: 23.81%
- overblocking: 0%

After first reveal the set became a regression set.

## Task-scoped authority reduction

Ten-task benchmark:
- inventory size: 487 capabilities
- mean authority reduction: 99.49%
- unnecessary standing-authority exposures removed across tasks: 4,845

Authority reduction measures how much standing capability surface is excluded from each compiled task capsule. It is not a security score.

## Framework equivalence

Equivalent capability definitions expressed as:
- generic JSON
- MCP
- OpenAI function tools
- Anthropic tools
- OpenAPI

produce:
- one semantic manifest digest
- one KCC inventory digest
- identical task-scoped grants
- identical generic Guard boundaries

Denied calls do not reach the caller-supplied dispatcher.

## Live MCP compatibility

Pinned published reference servers:
- Filesystem: 14 tools
- Memory: 9 tools
- Sequential Thinking: 1 tool

All completed live stdio discovery and produced deterministic inventory locks at the recorded checkpoint.

Fresh M2 discovery holdout:
- Everything server
- 13 tools discovered
- 0 expected source-bound tools missing

## Drift

Synthetic real-corpus drift recall at recorded checkpoint: 100%.

Published Filesystem comparison:
- 2026.7.10 -> 2026.8.31: no authority-contract drift detected
- 2026.1.14 -> 2026.8.31: 14/14 capability fingerprints changed while tool count remained 14

This shows that KCC does not treat a package version change itself as authority drift, while semantic capability-contract changes do affect the lock.

## M4 performance checkpoint

GitHub Actions microbenchmarks:
- authorize p95: approximately 0.012 ms
- compile p95: approximately 0.047 ms

These are microbenchmarks, not production throughput or latency guarantees.

## Interpretation

The v0.1 evidence supports the current engineering thesis:
KCC can normalize heterogeneous capability definitions, compile a much smaller task-scoped authority set, and enforce that boundary before host dispatch.

It does not establish that every unknown tool is correctly classified, that every agent framework is compatible, or that KCC replaces application-specific authorization and identity controls.
