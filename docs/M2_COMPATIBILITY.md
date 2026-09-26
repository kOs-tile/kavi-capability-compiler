# M2 Real MCP Compatibility

This checkpoint validates KCC live discovery against published, installable MCP servers rather than only local fixtures.

## Published server batch

Pinned npm packages:

- `@modelcontextprotocol/server-filesystem@2026.8.31`
- `@modelcontextprotocol/server-memory@2026.8.31`
- `@modelcontextprotocol/server-sequential-thinking@2026.8.31`

KCC performs only MCP initialization and `tools/list`. It does not call discovered tools.

## Verified result

All three published servers completed live stdio discovery through the official MCP Python client:

- Filesystem: 14 tools
- Memory: 9 tools
- Sequential Thinking: 1 tool
- negotiated protocol: `2025-11-25`
- every inventory was non-empty
- pinned expected tool registrations were present
- deterministic inventory locks were produced

## Compatibility failures found before green

### Source package version is not proof of registry installability

The repository package manifests reported development versions such as Filesystem `0.6.3`, but npm did not contain that Filesystem version. The first compatibility run failed with `npm notarget`.

KCC now records source provenance separately from the published package version used for executable compatibility tests.

### Documentation naming can differ from runtime registration

Sequential Thinking prose referred to `sequential_thinking`, while the runtime registration uses `sequentialthinking`.

Expected capability names are therefore bound to the runtime registration source rather than prose documentation.

## Method boundary

These tests prove protocol/discovery compatibility with these pinned published packages. They do not prove that every MCP server is compatible, and they do not authorize or execute any server tool.

A separate sealed M2 discovery holdout is used for a server not present in this compatibility batch.
