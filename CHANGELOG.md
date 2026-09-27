# Changelog

All notable changes to KAVI Capability Compiler are documented here.

## 0.1.0 — release candidate

### Added
- framework-neutral `kcc.capabilities.v1` manifest
- adapters for generic JSON, MCP tool definitions, OpenAI function tools, Anthropic tools, and OpenAPI
- deterministic capability fingerprints and inventory locks
- task-scoped execution capsules
- policy allow / deny / approval decisions
- operation and parameter constraints
- fail-closed runtime authorization
- embedded sync + async `Guard`
- explicit `ApprovalRequired` and `CapabilityDenied` host handoffs
- optional Ed25519 signed capsule envelopes
- optional live MCP stdio and Streamable HTTP discovery
- secret-safe MCP config summaries
- authority drift detection
- execution-evidence envelopes
- benchmark and holdout gates

### Distribution
- dependency-free default core install
- optional `mcp` and `signing` extras
- dependency-free wheel smoke
- Apache-2.0 license
- Python 3.11+

### Security model
- unknown authority never becomes silent authority
- denied calls do not reach the host dispatcher
- signed envelopes cannot self-declare a trusted key
- source provenance is separated from semantic authority fingerprints

### Known limits
- v0.1 is alpha software
- capability classification is deterministic and conservative, not a proof of tool safety
- KCC does not provide identity, KMS, secrets management, or a hosted approval service
- optional live discovery currently focuses on MCP
- no hosted control plane or dashboard is included
