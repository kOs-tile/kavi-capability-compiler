# M2 Live MCP Discovery

M2 moves KAVI Capability Compiler from static snapshots to authority observed from a running MCP server.

## Supported discovery paths

### stdio

`discover_stdio()` starts a local MCP server using the official Python SDK client lifecycle, initializes the session, calls `tools/list`, and normalizes the result into the KCC inventory IR.

Environment values are passed to the child process only. They are not copied into discovery output, inventory fingerprints, or lockfiles unless the server itself intentionally exposes those values in tool metadata.

### Streamable HTTP

`discover_streamable_http()` connects to a Streamable HTTP MCP endpoint through the official SDK. Optional HTTP headers are applied through an `httpx2.AsyncClient` and are never copied into the returned KCC artifact.

### Config-driven discovery

`discover_config_server()` accepts common `mcpServers` / `servers` configuration shapes and dispatches to stdio or Streamable HTTP.

`sanitize_mcp_config()` produces a shareable summary containing only:
- server names
- transport type
- command basename
- redacted argument shapes
- environment variable names
- URL origin only (scheme + host + optional port), plus path-segment count and query-key names
- HTTP header names

Secret values are excluded, including URL userinfo, path segment values, query values, environment values, header values, and positional argument values.

## CLI

Examples:

```bash
kcc discover-stdio python server.py -o discovery.json --lock-output inventory.lock.json
kcc discover-http http://127.0.0.1:8000/mcp -o discovery.json --lock-output inventory.lock.json
kcc discover-config mcp.json my-server -o discovery.json --lock-output inventory.lock.json
kcc config-summary mcp.json -o mcp.safe.json
```

The lockfile binds the exact live tool fingerprints observed during discovery.

## Drift behavior

The M2 integration fixture proves three live `tools/list` changes:

- added capability
- removed capability
- changed capability metadata

A prior inventory lock detects all three through `diff_inventory_lock()`.

New authority is never silently accepted by the lock comparison.

## Current boundary

This is a discovery and binding layer, not a general MCP proxy. KCC does not automatically execute arbitrary discovered server commands, persist credentials, or replace MCP server authentication.

Remaining M2 work includes:
- broader real-server discovery validation
- timeout/cancellation hardening
- config format coverage
- live drift evidence against non-fixture servers
- fresh sealed holdout before M2 exit
