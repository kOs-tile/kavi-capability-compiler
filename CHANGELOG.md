# Changelog

All notable changes to KAVI Capability Compiler are documented here.

## 0.2.0 — unreleased development line

### Added
- deterministic delegation-request and delegated-capsule contracts
- provable child-authority attenuation across capability, operation, parameter, lifetime, inventory, and trust boundaries
- additive public schemas `kcc.delegation-request.v1` and `kcc.delegated-capsule.v1`
- public `attenuate_capsule` and `verify_delegated_capsule` APIs
- safe coding-agent integration contract and copy/paste adoption path
- clean installed-wheel delegation-to-Guard runtime evidence
- credential-free real-consumer exchange execution boundary case study
- public `capability_id(...)` utility for deterministic external capability identity construction

### Security
- delegated authority must remain a deterministic subset of verified parent grants
- parent approval/deny authority cannot be upgraded into child grants
- ambiguous or unsupported attenuation comparisons fail closed
- structured-parent to scalar-child attenuation is rejected in v1 to avoid Python equality alias widening such as `1 == True` and `1 == 1.0`
- child lifetime is clamped to parent expiry and inventory drift invalidates delegation verification
- explicit exchange/trading order mutations are classified as financial/high-impact while generic work-order creation and order-status reads retain their narrower semantics
- real-consumer exchange dogfood proves wrong symbol, side, quantity, and ungranted order-mode calls are blocked before host dispatch

### Evidence
- clean installed-wheel delegated child executes through the public Guard with denied widening reaching the host zero times
- first real-consumer authority misclassification was minimized into a deterministic regression fixture
- real-consumer exchange execution authority is representable with current framework-neutral contracts without a new core dependency

### Compatibility
- canonical capability ID behavior is unchanged; v0.2 exposes the existing constructor publicly so external planners do not have to copy a private normalization rule
- existing `kcc.capsule.v1` and `kcc.sdk.v1` contracts remain intact
- no new required core dependency
- latest published stable release remains v0.1.1 until v0.2.0 publication gates are completed

## 0.1.1 — security patch

### Security
- reject unsupported or malformed structured parameter predicates at capsule compile time instead of allowing them to be silently ineffective
- fail closed with `parameter_type_mismatch:<name>` when runtime values cannot be evaluated against numeric or length bounds

### Compatibility
- preserve `kcc.sdk.v1`
- preserve `kcc.capabilities.v1`, `kcc.inventory.v1`, `kcc.inventory-lock.v1`, `kcc.capsule.v1`, and `kcc.signed-capsule.v1`
- no new required core dependency
- no framework-specific core dependency

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
- pre-publication security hardening for canonical capability identities and authority-artifact integrity
- remote MCP discovery transport protection: HTTPS required outside loopback and URL userinfo rejected

### Distribution
- dependency-free default core install
- optional `mcp` and `signing` extras
- dependency-free wheel smoke
- bit-for-bit release-artifact CI gate: raw reproducible wheels plus commit-epoch-canonicalized sdists
- Twine release-metadata validation
- wheel-surface audit excluding repository-only validation/example/test content
- immutable-SHA GitHub Actions with checkout credential persistence disabled
- dependency-vulnerability audit for the resolved optional runtime dependency set
- clean CPython 3.11–3.14 wheel/core/signing/MCP-extra compatibility matrix
- clean source-distribution install smoke
- Apache-2.0 license
- Python 3.11+

### Security model
- capsule authorization rejects unsupported contract versions and missing `fail_closed=true` even when integrity is recomputed
- signed capsules are bound to `kcc.capsule.v1`
- unknown authority never becomes silent authority
- denied calls do not reach the host dispatcher
- signed envelopes cannot self-declare a trusted key
- source provenance is separated from semantic authority fingerprints
- manifest, inventory, and inventory-lock integrity is enforced before authority compilation/use
- canonical capability identity aliases and reserved-delimiter collisions fail closed
- signing extra requires vulnerability-audited `cryptography>=50.0.1,<51`

### Known limits
- v0.1 is alpha software
- capability classification is deterministic and conservative, not a proof of tool safety
- KCC does not provide identity, KMS, secrets management, or a hosted approval service
- optional live discovery currently focuses on MCP
- no hosted control plane or dashboard is included
