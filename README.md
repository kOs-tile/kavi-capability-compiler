# KAVI Capability Compiler

> **Status — Active flagship.** M0, M1, and M2 exit gates are CI-backed and passed. M3A KAVI control-plane dogfood passed; M3B authenticated live observation is probe-ready and remains pending secure bearer availability.

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
- deterministic `kavi.execution-evidence.v0` envelope
- binds ORACLE, MNEMOS, SPECTRAFLOW, PHANTOM, and NEPHILIM artifact digests to one execution + capsule
- evidence envelope integrity verification
- explicit `authority_granted=false` invariant
- CLI: `kcc evidence-bind` and `kcc evidence-verify`
- executable regression proving external evidence cannot expand a compiled KCC grant

### M3 framework-agnostic integration
- universal `kcc.capabilities.v1` capability manifest
- adapters for MCP, OpenAI function tools, Anthropic tools, OpenAPI, and generic JSON
- semantic fingerprints independent of source format/provenance
- generic runtime guard in front of any caller-supplied dispatcher
- cross-format equivalence benchmark

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

M2's recorded exit gate passes. M3 now focuses on a universal capability contract so existing runtimes can integrate without framework migration. Specific agent systems are optional validation targets.

See `docs/M2_EXIT.md`, `docs/RUNTIME_AUTHORIZATION.md`, and `docs/EXECUTION_EVIDENCE.md`.

## KAVI ecosystem

KCC stays independent of the surrounding research stack. Integration responsibilities and non-goals are documented in `docs/KAVI_ECOSYSTEM.md`.


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
guard = kcc.Guard.from_capsule(capsule)

result = await guard.dispatch(
    capability_id,
    existing_dispatcher,
    parameters=tool_arguments,
)
```

KCC does not own the model, dispatcher, credentials, filesystem, or deployment. See `docs/EMBEDDED_SDK.md`.
