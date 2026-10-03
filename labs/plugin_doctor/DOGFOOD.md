# Plugin Doctor V0 dogfood log

## Baseline A — Swift Concurrency Agent Skill

Repository: https://github.com/AvdLee/Swift-Concurrency-Agent-Skill

Observed public package surface at commit `d5770817d2622e1585b1f7eaebc791a9cb0959c8`:

- root `plugin.json` declares Agent Plugins schema 1.0.0;
- plugin name: `swift-concurrency`;
- explicit version: `2.3.0`;
- root description is nonempty;
- skill manifest exists at `skills/swift-concurrency/SKILL.md`;
- skill front matter declares both `name` and `description`;
- repository README states the plugin is published in the OpenAI Plugins Directory.

Purpose: clean skills-only baseline for the GitHub/package ingestion path.

Expected V0 package outcome: no structural blocker from the currently implemented package rules.

This expectation must be checked through the runnable GitHub ingestion path before it becomes a benchmark assertion. Do not convert it into a performance or approval claim.

## Next dogfood classes

1. clean skills-only plugin;
2. clean remote-MCP plugin;
3. malformed package with known submission errors;
4. plugin with ambiguous tool authority;
5. plugin with mutating/destructive tools;
6. tool set designed to trigger positive and negative invocation eval cases.

Only reproducible results are eligible for public content claims.
