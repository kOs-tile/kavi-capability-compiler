# Changelog

All notable changes to KAVI Capability Compiler are documented here.

## 0.1.0 — release candidate

### Added
- framework-neutral `kcc.capabilities.v1` manifest
- versioned `kcc.inventory.v1`, `kcc.inventory-lock.v1`, and `kcc.capsule.v1` authority contracts
- packaged JSON Schemas for capability manifests, inventories, inventory locks, capsules, and signed capsules
- explicit `kcc.sdk.v1` compatibility and authorization-exception semantics
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
- inventory-bound Guard drift enforcement
- adversarial SDK benchmark with explicit replay and direct-dispatch trust boundaries
- executable framework-neutral integration kits for Generic Python, OpenAI tool shapes, Anthropic tool shapes, MCP definitions, and OpenAPI
- pinned repository-only runtime validation for OpenAI Agents SDK 0.22.3 FunctionTool dispatch
- pinned repository-only runtime validation for Anthropic Python SDK 1.8.0 beta-tool dispatch
- pinned repository-only runtime validation for LangGraph 1.2.12 ToolNode dispatch

### Distribution
- dependency-free default core install
- optional `mcp` and `signing` extras
- dependency-free wheel smoke
- bit-for-bit release-artifact CI gate: raw reproducible wheels plus commit-epoch-canonicalized sdists
- Twine release-metadata validation
- wheel-surface audit excluding repository-only validation/example/test content
- Apache-2.0 license
- Python 3.11+

### Security model
- capsule authorization rejects unsupported contract versions and missing `fail_closed=true` even when integrity is recomputed
- signed capsules are bound to `kcc.capsule.v1`
- unknown authority never becomes silent authority
- denied calls do not reach the host dispatcher
- signed envelopes cannot self-declare a trusted key
- source provenance is separated from semantic authority fingerprints
- public capsule verification validates supplied inventory integrity
- inventory-lock drift verification validates lock and current-inventory integrity
- authenticated non-loopback MCP discovery requires HTTPS and rejects URL userinfo credentials
- GitHub Actions are pinned to immutable commit SHAs and checkout credentials are not persisted
- release build/check tooling is version-pinned
- security-sensitive optional dependency floors exclude known affected httpx2 and cryptography ranges at the v0.1 security preflight

### Known limits
- v0.1 is alpha software
- capability classification is deterministic and conservative, not a proof of tool safety
- KCC does not provide identity, KMS, secrets management, or a hosted approval service
- optional live discovery currently focuses on MCP
- no hosted control plane or dashboard is included
