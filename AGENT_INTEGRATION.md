# Agent-assisted KCC integration

This document is for coding agents integrating KAVI Capability Compiler into an existing agent application.

The goal is not to redesign the host application. The goal is to place a deterministic least-authority boundary immediately before the host's real tool dispatcher and prove that denied calls cannot reach it.

## Stable vs development source

Default to the latest published stable release:

`v0.1.1`

Install the stable core with:

```bash
python -m pip install --index-url https://kos-tile.github.io/kavi-capability-compiler/simple/ "kavi-capability-compiler==0.1.1"
```

Do not use repository main or unreleased v0.2 behavior unless the user explicitly asks to test development code and accepts an unreleased API surface.

## Integration invariant

For every protected tool call:

```
model / planner
    -> proposed capability + parameters
    -> KCC Guard
    -> authorized? yes -> host dispatcher
                   no  -> stop
```

A protected denied call must never reach the host dispatcher.

Do not leave a parallel direct-dispatch path that can bypass Guard for the same protected capabilities.

## Required integration sequence

### 1. Recover the actual execution architecture

Before changing code, identify:

- where tools/capabilities are declared;
- which framework shape is in use: generic Python, OpenAI-shaped tools, Anthropic-shaped tools, MCP, OpenAPI, LangGraph, or a custom dispatcher;
- the exact function/method that performs real side effects;
- whether there are multiple dispatch paths;
- how task intent is represented;
- where policy should live;
- which tests currently exercise tool execution.

Do not assume the first tool registry you find is the real execution boundary.

### 2. Establish a clean baseline

Run the existing test suite before integration.

Record:

- current passing/failing tests;
- current package/runtime environment;
- tool/capability count if available;
- known direct-dispatch entry points.

Do not attribute pre-existing failures to KCC.

### 3. Install stable KCC

Prefer the exact published stable version above.

The default KCC core has no required third-party runtime dependency.

Use optional extras only when the target integration actually requires them. Do not add framework dependencies to KCC core.

### 4. Normalize the observed capability surface

Use the closest existing KCC adapter instead of inventing a framework-specific authority model.

Example:

```python
import kavi_capability_compiler as kcc

manifest = kcc.adapt_capabilities(
    "openai",
    {"tools": existing_agent_tools},
    namespace="my-agent",
)

inventory = kcc.scan_manifest(manifest)
```

Use another supported source format when appropriate.

Do not silently discard unknown capabilities. Unknown authority must remain fail-closed.

### 5. Audit before enforcement

Inspect the resulting inventory and KCC audit output before wiring Guard into production dispatch.

Identify:

- read-only capabilities;
- writes/mutations;
- deletes;
- financial/high-impact operations;
- mixed or unknown authority;
- capabilities with missing or weak parameter schemas.

Do not convert unknown authority into allow merely to make integration easier.

### 6. Define explicit task intent and deterministic policy

KCC requires explicit authority intent and policy.

If the target project already has task-level permission semantics, map them into KCC.

If it does not, create a bounded policy scaffold but do not invent broad wildcard allow rules.

When required authority cannot be determined safely, stop at audit/scaffold mode and report the unresolved policy decision to the user.

Example compile flow:

```python
capsule = kcc.compile_capsule(
    inventory,
    task_intent,
    policy,
)
```

### 7. Put Guard at the real dispatcher boundary

Create an inventory-bound Guard:

```python
guard = kcc.Guard.from_capsule(
    capsule,
    inventory=inventory,
)
```

Route the protected call through Guard immediately before the real host dispatcher:

```python
result = await guard.dispatch(
    capability_id,
    existing_dispatcher,
    operation=operation,
    parameters=tool_arguments,
)
```

Do not authorize one parameter mapping and dispatch a different one.

Do not catch KCC denial and then execute the tool anyway.

Do not reinterpret approval-required as allow.

### 8. Prove the boundary with tests

Add regression tests for the host integration.

At minimum prove:

1. a granted call reaches the dispatcher exactly once;
2. a denied capability reaches the dispatcher zero times;
3. approval-required reaches the dispatcher zero times;
4. an operation outside the capsule reaches the dispatcher zero times;
5. an unexpected or invalid parameter fails closed before dispatch;
6. an expired capsule fails closed;
7. inventory/fingerprint drift fails closed when using an inventory-bound Guard;
8. no alternate protected execution path bypasses Guard.

Preserve existing application tests.

### 9. Run adversarial checks

Try to widen authority deliberately:

- call a capability absent from grants;
- use a broader operation;
- add an unexpected parameter;
- exceed numeric/length bounds;
- alter inventory/tool definition after compilation;
- tamper with the capsule;
- reuse expired authority.

The expected result is denial before dispatcher execution.

### 10. Return an integration report

Do not finish with only "installed successfully."

Report:

- KCC version installed;
- framework/adapter path used;
- files changed;
- observed capability count;
- dispatcher boundary protected;
- number of direct-dispatch paths found;
- remaining bypasses, if any;
- policy assumptions;
- tests added and results;
- examples of granted and denied calls;
- whether production enforcement was enabled or integration stopped in audit/scaffold mode.

If dispatcher coverage cannot be proven, say so explicitly.

## Security boundaries

KCC does not make model output correct.

KCC does not replace IAM, secret management, identity, KMS, sandboxing, or host authorization.

KCC constrains what a specific execution is authorized to dispatch.

Do not claim certification, complete framework coverage, or universal security from a successful integration.

## Copy/paste task for a coding agent

Use the prompt below in a coding agent that has access to the target repository:

```text
Integrate KAVI Capability Compiler into this project using the stable v0.1.1 release.

Reference:
https://github.com/kOs-tile/kavi-capability-compiler
Read AGENT_INTEGRATION.md in that repository before changing code.

Requirements:
- preserve existing application behavior unless a change is required to enforce the authority boundary;
- first identify the real tool-dispatch boundary and every parallel path that can execute protected tools;
- install stable KCC v0.1.1, not unreleased main/v0.2 code;
- adapt the existing tool surface with the closest framework-neutral KCC adapter;
- build an inventory and audit it before enabling enforcement;
- do not invent broad wildcard allow policy;
- unknown authority must remain fail-closed;
- if safe task intent/policy cannot be derived from existing explicit application semantics, stop in audit/scaffold mode and report what decision is missing;
- place an inventory-bound Guard immediately before the real dispatcher;
- denied or approval-required calls must never reach the dispatcher;
- authorize and dispatch the exact same parameter mapping;
- add regression tests proving granted dispatch count = 1 and denied dispatch count = 0;
- test operation constraints, parameter constraints, expiry, tamper/integrity failure, and inventory drift where applicable;
- verify there is no remaining protected direct-dispatch bypass;
- run the existing test suite plus the new integration tests;
- do not claim success if dispatcher coverage cannot be proven.

At the end, report:
1. files changed,
2. KCC version,
3. adapter/framework path,
4. observed capability count,
5. protected dispatcher boundary,
6. policy assumptions,
7. tests and results,
8. any remaining bypass or unresolved authority decision.
```

## Further reference

- `README.md`
- `docs/EMBEDDED_SDK.md`
- `docs/INTEGRATION_RECIPES.md`
- `docs/SDK_COMPATIBILITY.md`
- `docs/ADVERSARIAL_SDK.md`
- `SECURITY.md`
