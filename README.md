# KAVI Capability Compiler

> **Status — v0.1 technical release candidate.** Core contracts, adversarial enforcement, framework-neutral integration kits, three pinned real-runtime validations, and reproducible release-artifact checks are CI-gated. Tag/GitHub Release/PyPI publication remain founder-gated.

KCC is a framework-agnostic **least-authority compiler for AI agents**.

```
discover/scan -> audit -> compile -> execution capsule -> verify/authorize
                                                   \
                                                    -> execution evidence
```

Given an observed capability surface, explicit task intent, and deterministic policy, KCC compiles a bounded authority artifact for one execution.

## Why

Agent systems accumulate standing authority through MCP servers, tools, credentials, APIs, filesystem access, skills, and sub-agents. Runtime gates ask whether a particular call should execute. KCC focuses on the earlier question:

> Why did this execution have this capability in the first place?

## What is shipped

### Compiler kernel
- MCP snapshot -> canonical capability inventory
- deterministic effect + risk evidence analysis
- task intent + policy -> execution capsule
- deny precedence and fail-closed unknown authority
- operation and parameter constraints
- capability fingerprints and capsule integrity
- runtime `authorize_call` primitive
- portable fail-closed runtime guard that blocks before dispatcher execution
- inventory locks and drift diff

### M1 evidence
- 487 sourced capabilities across 30 MCP surfaces
- 173 dangerous samples
- 0 observed false-safe outcomes
- 100% dangerous-capability recall on the development corpus
- 99.49% mean authority reduction across the 10-task benchmark
- first sealed classification holdout: 63 unseen capabilities, 0 false-safe

These are benchmark checkpoint measurements, not production security guarantees. See `docs/M1_EXIT.md`.

### M2 live discovery
- official MCP Python SDK stdio discovery
- Streamable HTTP discovery
- config-driven discovery
- secret-safe config summaries
- live discovery -> deterministic inventory lock
- live added/removed/changed authority detection
- bounded discovery timeouts
- published official MCP compatibility validation

### Execution evidence
- deterministic execution-evidence envelope
- binds external evidence artifact digests to one execution + capsule
- evidence envelope integrity verification
- evidence is explicitly non-authoritative and cannot expand a compiled grant
- CLI: `kcc evidence-bind` and `kcc evidence-verify`

### M3 framework-agnostic integration
- universal `kcc.capabilities.v1` capability manifest
- versioned `kcc.inventory.v1`, `kcc.inventory-lock.v1`, and `kcc.capsule.v1` contracts
- adapters for MCP, OpenAI function tools, Anthropic tools, OpenAPI, and generic JSON
- semantic fingerprints independent of source format/provenance
- generic runtime guard in front of any caller-supplied dispatcher
- cross-format equivalence benchmark
- inventory-bound Guard for post-compile capability drift
- adversarial SDK benchmark with explicit host-responsibility boundaries
- executable integration kits for Generic Python, OpenAI tool shapes, Anthropic tool shapes, raw MCP definitions, and OpenAPI
- repository-only validation against real OpenAI Agents SDK `FunctionTool` objects
- repository-only validation against real Anthropic Python SDK `@beta_tool` objects
- repository-only validation immediately before real LangGraph `ToolNode.invoke()` dispatch

KAVI/Hermes/Codex integrations are validation targets and examples, not dependencies of the compiler.

## Security invariant

**Unknown authority never becomes silent authority.**

Uncertain authority fails closed into denial/approval behavior rather than becoming an automatic grant.

## Quick start

Python 3.11+.

Default install is the embedded core SDK and has no required third-party runtime dependencies:

```bash
pip install kavi-capability-compiler
```

Optional extras:

```bash
pip install "kavi-capability-compiler[mcp]"
pip install "kavi-capability-compiler[signing]"
```

For repository development:

```bash
python -m pip install -e ".[all]"
pytest -q

# Static snapshot
kcc scan tests/fixtures/mcp_snapshot.json -o inventory.json
kcc audit inventory.json -o audit.json
kcc compile inventory.json --intent examples/intent.json --policy examples/policy.json -o capsule.json
kcc verify capsule.json --inventory inventory.json

# Live MCP discovery
kcc discover-stdio python tests/fixtures/live_mcp_server.py \
  -o discovery.json --lock-output inventory.lock.json

kcc config-summary mcp.json -o mcp.safe.json
kcc discover-config mcp.json my-server \
  -o discovery.json --lock-output inventory.lock.json
```

## Current boundary

KCC is not a hosted gateway, desktop service, local daemon, IAM replacement, secret manager, or autonomous remediation system. Live discovery does not automatically execute discovered tools. Runtime enforcement is intentionally a small portable primitive.

M0–M10 engineering is complete. M11 closes reproducible release engineering and metadata verification; external publication remains a separate founder approval.

See `docs/EMBEDDED_SDK.md`, `docs/SDK_COMPATIBILITY.md`, `docs/ADVERSARIAL_SDK.md`, `docs/UNIVERSAL_MANIFEST.md`, `docs/INTEGRATION_RECIPES.md`, `docs/OPENAI_AGENTS_VALIDATION.md`, `docs/ANTHROPIC_SDK_VALIDATION.md`, `docs/LANGGRAPH_TOOLNODE_VALIDATION.md`, `docs/EXTERNAL_VALIDATION_V0.1.md`, and `docs/BENCHMARK_REPORT_V0.1.md`.

## Embed it into an existing agent

The primary integration model is in-process:

```python
import kavi_capability_compiler as kcc

manifest = kcc.adapt_capabilities(
    "openai",
    {"tools": existing_agent_tools},
    namespace="my-agent",
)
inventory = kcc.scan_manifest(manifest)
capsule = kcc.compile_capsule(inventory, task_intent, policy)
guard = kcc.Guard.from_capsule(capsule, inventory=inventory)

result = await guard.dispatch(
    capability_id,
    existing_dispatcher,
    parameters=tool_arguments,
)
```

KCC does not own the model, dispatcher, credentials, filesystem, or deployment. See `docs/EMBEDDED_SDK.md`.
