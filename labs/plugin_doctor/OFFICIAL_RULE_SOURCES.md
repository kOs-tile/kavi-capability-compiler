# Plugin Doctor rule sources

Plugin Doctor separates two kinds of findings:

1. **Source-linked rules** — directly grounded in published platform requirements.
2. **Heuristics** — KAVI readiness/discovery checks that are useful but are not represented as OpenAI policy.

## Current official sources

### OpenAI Plugin Guidelines
https://developers.openai.com/plugins/plugin-guidelines

V0 checks currently derived from this source:

- every tool needs a nonempty, accurate description;
- tool annotations must explicitly set `readOnlyHint`, `destructiveHint`, and `openWorldHint` to boolean values;
- side effects must not be hidden;
- write/destructive capability surfaces require explicit caution and accurate metadata;
- model-readable fields must not manipulate fair plugin selection.

### OpenAI Remote MCP Server Review Requirements
https://developers.openai.com/plugins/deploy/app-review

Used as the source for submission-readiness metadata and the future submission bundle validator.

### OpenAI Plugin Packaging
https://developers.openai.com/plugins/build/plugins

Future package-level checks will validate:

- root `plugin.json`;
- portable Agent Plugins schema;
- root `mcp.json` when bundled MCP is used;
- skills placement;
- OpenAI-specific extension placement.

### OpenAI Skills Guidance
https://developers.openai.com/plugins/build/skills

Future eval checks will cover direct activation, indirect activation, incomplete-input behavior, negative activation, and edge cases.

## Evidence rule

No Plugin Doctor finding should be presented as an OpenAI requirement unless it carries an official source URL.

Heuristic findings remain labeled as KAVI readiness checks.

The numeric score is never represented as an OpenAI approval probability.
