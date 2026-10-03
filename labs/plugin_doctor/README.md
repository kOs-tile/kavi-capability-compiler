# Plugin Doctor V0 incubation

This directory is an isolated product experiment built on top of KCC.

It must not change KCC compiler or Guard semantics.

## Current V0 surfaces

- static tool/capability readiness audit
- official-rule-linked OpenAI annotation checks
- portable `plugin.json` / `mcp.json` package validation
- skill layout/front-matter validation
- safe local package ingestion
- bounded GitHub repository ingestion
- remote MCP discovery without invoking discovered tools
- injectable positive/negative invocation eval harness
- deterministic lexical baseline for CI

## Run

From the repository root:

```bash
# Local portable plugin
python -m labs.plugin_doctor.cli package ./my-plugin

# Public GitHub plugin package
python -m labs.plugin_doctor.cli github https://github.com/OWNER/REPO

# Private GitHub repo: token is request-only and never returned
GITHUB_TOKEN=... python -m labs.plugin_doctor.cli github https://github.com/OWNER/REPO

# Remote MCP endpoint (requires KCC MCP extra)
python -m labs.plugin_doctor.cli mcp https://example.com/mcp

# Raw tool definitions
python -m labs.plugin_doctor.cli source tools.json --format generic --namespace demo
```

## Tests

```bash
pytest -q \
  tests/test_plugin_doctor_incubation.py \
  tests/test_plugin_doctor_package.py \
  tests/test_plugin_doctor_evals.py \
  tests/test_plugin_doctor_ingest.py
```

## First public dogfood target

`https://github.com/AvdLee/Swift-Concurrency-Agent-Skill`

This is useful as a clean skills-only baseline because the public repository uses a root portable `plugin.json` and `skills/swift-concurrency/SKILL.md`. Its README states the plugin is published in the OpenAI Plugins Directory.

Run:

```bash
python -m labs.plugin_doctor.cli github \
  https://github.com/AvdLee/Swift-Concurrency-Agent-Skill
```

The dogfood target is evidence for package/readiness behavior only. It is not an endorsement, ranking, or claim about OpenAI review internals.

See `docs/PLUGIN_DOCTOR_V0.md` for the product contract and `OFFICIAL_RULE_SOURCES.md` for policy-source boundaries.
