# KAVI Plugin Doctor — V0 Product Brief

Status: **ACTIVE / INCUBATION**
Branch: `product/plugin-doctor-v0`
Boundary: KCC kernel remains unchanged. Plugin Doctor consumes KCC as a product-layer dependency.

## Thesis

ChatGPT's plugin ecosystem is creating a new distribution surface for SaaS and developer tools, but shipping a reliable plugin requires more than exposing an MCP server.

Developers need a fast answer to:

> Is this plugin safe, understandable to the model, testable, and ready to ship?

KAVI Plugin Doctor turns a plugin/MCP capability surface into an inspectable readiness report.

## Target users

1. Developers shipping ChatGPT/Codex plugins.
2. SaaS teams exposing an existing API through MCP.
3. Agent-infrastructure teams reviewing tool authority before release.
4. Agencies building plugins for clients.

## V0 user promise

Input one supported capability surface and receive:

- normalized tool inventory
- authority/effect classification
- security findings
- schema/readiness findings
- discovery-description findings
- deterministic score
- SHIP / FIX / BLOCKED state
- machine-readable report suitable for a future shareable scorecard

## V0 architecture

```
plugin / MCP / tool definitions
            |
            v
     source adapter
            |
            v
   kcc.capabilities.v1
            |
            v
    kcc.inventory.v1
            |
      +-----+------+
      |            |
      v            v
 KCC audit     Doctor rules
 authority     readiness /
 + risk        discovery
      |            |
      +-----+------+
            |
            v
 plugin-doctor.report.v0
            |
            v
    score + state + fixes
```

KCC remains framework-agnostic and product-neutral. Plugin Doctor owns UX-oriented readiness rules, scoring, OpenAI-specific policy mapping, synthetic invocation evals, and report presentation.

## Scoring

V0 uses a transparent heuristic score from 0–100. It is not an OpenAI approval prediction.

Initial dimensions:

- Safety / authority: 35
- Tool/schema quality: 25
- Review-readiness: 20
- Discovery metadata: 10
- Eval readiness: 10

A deterministic blocker can force `BLOCKED` regardless of numeric score.

## V0 scope

### In

- generic/OpenAI/Anthropic/OpenAPI/MCP capability definitions already supported by KCC
- KCC inventory + authority audit
- missing/weak description checks
- missing/unbounded schema checks
- unknown/mixed authority surfacing
- annotation conflicts
- high-impact/mutating capability visibility
- deterministic readiness score
- structured remediation hints
- tests proving deterministic output

### Next slices

- public MCP endpoint ingestion
- GitHub repository ingestion
- official ChatGPT plugin manifest/skill checks
- source-linked OpenAI submission-rule checks
- synthetic invocation evals
- false-positive / false-negative invocation tests
- model-facing description optimization
- shareable public scorecard
- "generate fixes" patch bundle
- hosted ChatGPT plugin surface

### Explicit non-goals for V0

- changing KCC's compiler semantics
- auto-publishing or auto-submitting plugins
- claiming guaranteed OpenAI approval
- executing discovered write tools
- handling secrets or storing customer credentials
- enterprise RBAC/team billing

## Safety boundary

Plugin Doctor analyzes capability metadata by default. Discovery must not execute discovered tools.

Unknown authority is never silently marked safe. KCC's fail-closed invariant remains authoritative.

## V0 acceptance tests

V0 is complete when:

1. A supported tool definition can be normalized through KCC.
2. The same input always produces the same score and findings.
3. An unknown-effect tool cannot receive a SHIP result.
4. Missing descriptions and missing schemas are surfaced.
5. High-impact tools are visible and reduce readiness.
6. Clean read-only tools with bounded schemas can receive SHIP.
7. The report is valid structured JSON.
8. Existing KCC tests remain unchanged and passing.

## Product loop

```
free audit
   |
   v
shareable scorecard
   |
   v
developer distribution
   |
   v
real failure corpus
   |
   +--> better Doctor rules
   +--> KCC regression evidence
   +--> technical content
   +--> custom plugin implementation leads
```

## Commercial path

Free:
- audit
- score
- prioritized findings
- shareable result

Paid service:
- plugin remediation
- OAuth / tool redesign
- safe write actions
- eval suite
- deployment
- submission support

Later product:
- continuous plugin regression checks
- discovery/invocation monitoring
- organization policies
- CI gate

## Distribution/content engine

The product should create evidence, not generic AI content.

Examples after enough real audits exist:

- "I audited 100 ChatGPT plugins. Here are the most common authority mistakes."
- "Your MCP server works. That does not mean ChatGPT will invoke it correctly."
- "Most tool descriptions are written for humans. The model is also a consumer."
- "These plugin patterns consistently create unnecessary authority."
- benchmark reports generated from anonymized/consented public inputs

No benchmark claim is published without reproducible evidence.

## Extraction rule

This branch is an incubation surface only.

Once the first end-to-end audit passes its tests, Plugin Doctor should move into a standalone product repository and consume a pinned KCC release rather than becoming part of the KCC kernel.
