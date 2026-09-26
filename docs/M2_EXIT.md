# M2 Exit Report — Live MCP Discovery + Authority Drift

M2 moves KCC from static capability snapshots to authority observed from running MCP servers.

## Live transports

Verified:
- stdio MCP initialization and `tools/list`
- Streamable HTTP initialization and `tools/list`
- authenticated HTTP headers through an in-memory client
- bounded discovery timeout
- fail-closed connection/protocol errors

## Secret-safe config import

Supported common config containers:
- `mcpServers`
- `servers`
- `url`
- `serverUrl`
- stdio command / args / env
- HTTP headers

Persisted summaries exclude environment values, header values, URL userinfo, path values, query values, and positional argument values.

Config-driven discovery uses raw secret values only in memory for the immediate transport operation.

## Live lock and drift

A live discovery result can be compiled directly into a deterministic inventory lock.

Local live-server integration proves detection of:
- added authority
- removed authority
- changed capability metadata

Published-version evidence:
- Filesystem `2026.7.10 -> 2026.8.31`: clean; same 14-tool authority contract
- Filesystem `2026.1.14 -> 2026.8.31`: 14 tools before and after, but **14 changed capability fingerprints**

KCC therefore detects authority-contract drift even when tool IDs and tool count remain stable, while avoiding false drift from version numbers alone.

## Real published-server compatibility

Pinned official MCP packages were discovered without executing tools:

- Filesystem `2026.8.31`: 14 tools
- Memory `2026.8.31`: 9 tools
- Sequential Thinking `2026.8.31`: 1 tool

All negotiated MCP protocol `2025-11-25` and produced deterministic inventory locks.

Two compatibility failures were useful:
1. development package versions in repository manifests were not necessarily published npm versions;
2. prose documentation for Sequential Thinking used a different spelling from runtime registration.

KCC compatibility evidence now binds installable package versions separately from pinned runtime/source evidence.

## Fresh M2 discovery holdout

The Everything-server manifest was committed before first execution.

First reveal:
- package: `@modelcontextprotocol/server-everything@2026.8.31`
- live discovery: PASS
- protocol: `2025-11-25`
- discovered tools: 13
- expected source-bound tools missing: 0
- inventory + lock generation: PASS
- tool execution: none

After first reveal this becomes a regression target.

## Regression stack retained

At the recorded M2 checkpoint:
- full test suite: **33 passed**
- live discovery integration suite: **11 passed**
- M1 development corpus: 487 capabilities / 30 surfaces
- M1 dangerous recall: 100%
- M1 false-safe: 0
- sealed classification holdout false-safe: 0
- mean task authority reduction: 99.49%
- synthetic corpus drift recall: 100%
- authorize p95: ~0.028 ms
- compile p95: ~0.078 ms

Performance measurements are GitHub Actions microbenchmarks, not production throughput guarantees.

## M2 verdict

M2 exit gate passes.

KCC can now observe a running MCP capability surface, produce a deterministic authority inventory and lock, detect later authority-contract drift, and do so without persisting transport secret values.

The next stage is **M3 Hermes dogfood**. Hermes is used only as a real proving ground; the KCC core remains framework-agnostic.

M3 should prove one bounded workflow end to end:

`Hermes surface -> live/adapter inventory -> task intent -> capsule -> runtime guard -> allowed operation succeeds / outside-capsule operation is blocked`.
