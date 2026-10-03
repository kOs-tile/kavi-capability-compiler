# Plugin Doctor rule sources

Plugin Doctor separates three kinds of checks:

1. **Portable package conformance** — grounded in the Agent Plugins 1.0 schemas.
2. **OpenAI source-visible directory readiness** — rules that can be verified from repository/package content.
3. **Heuristics / portal-dependent checks** — either KAVI readiness signals or requirements that a repository audit cannot verify.

## Current official sources

### Agent Plugins 1.0 schemas

- https://agent-plugins.org/schemas/1.0.0/plugin.schema.json
- https://agent-plugins.org/schemas/1.0.0/mcp.schema.json

Portable package checks use these schemas as the canonical contract. In particular:

- the portable plugin name syntax allows the schema's dot/hyphen form;
- `version`, root `description`, and root `author` are optional in the Agent Plugins portable schema;
- portable MCP manifests use `mcpServers` and the declared transport variants.

### OpenAI Plugin Guidelines

https://developers.openai.com/plugins/plugin-guidelines

Source-visible checks derived from this source include:

- every model-callable tool needs an accurate description;
- `readOnlyHint`, `destructiveHint`, and `openWorldHint` must be explicit booleans;
- side effects and authority boundaries must not be hidden;
- model-readable fields must not manipulate fair plugin selection;
- tools should expose individual operations rather than a generic hidden executor.

### OpenAI submission field reference

https://developers.openai.com/plugins/deploy/submission

Plugin Doctor distinguishes package fields from portal state:

- submission-safe package names use lowercase letters/numbers and single hyphens;
- use an explicit semantic version for submission and updates;
- root Agent Plugins `description` and `author` remain optional portable fields;
- listing metadata such as `displayName`, `shortDescription`, `longDescription`, `developerName`, and `category` can be embedded under `extensions.com.openai.interface`;
- submission/review information may also be completed in the OpenAI portal.

A repository-only audit therefore reports whether embedded listing metadata appears complete, but does **not** turn absent portal metadata into a package blocker. `SHIP` means no source-visible blockers were found, not that portal submission is complete.

### OpenAI submission errors

https://developers.openai.com/plugins/deploy/submission-errors

Used for source-visible package/submission errors and to track portal-only requirements such as scans and domain verification.

### OpenAI Remote MCP Server Review Requirements

https://developers.openai.com/plugins/deploy/app-review

Used for remote MCP review boundaries and future portal/readiness checks.

### OpenAI Skills Guidance

https://developers.openai.com/plugins/build/skills

Eval checks cover direct activation, indirect activation, incomplete-input behavior, negative activation, and edge cases.

## Current official-doc conflict: annotation justifications

Checked 2026-10-03.

The current Plugin Guidelines state that annotation justifications are **no longer required**. The current Submission Errors page still lists a `justification_required` error, and the Remote MCP review page still discusses justification text.

Because the official sources currently conflict, Plugin Doctor does **not** treat missing annotation justification as a hard source-visible blocker. The explicit boolean annotations themselves remain enforced. Revisit this rule when the official documentation converges.

## Evidence rule

No Plugin Doctor finding should be presented as an OpenAI requirement unless it carries an official source URL.

Heuristic findings remain labeled as KAVI readiness checks. Portal-dependent state that cannot be inferred from source remains explicitly unverified.

The numeric score measures unique rule coverage. Repeated instances of the same rule remain visible as findings/blockers but do not repeatedly deduct score. The score is never represented as an OpenAI approval probability.
