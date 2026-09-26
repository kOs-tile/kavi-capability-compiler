# M2 Discovery Holdout — First Reveal

The manifest was committed before the first evaluator run.

## Frozen target

- package: `@modelcontextprotocol/server-everything@2026.8.31`
- expected registrations were bound to pinned source blobs:
  - `echo`
  - `get-sum`
  - `get-env`

## First result

- live stdio initialization: PASS
- `tools/list`: PASS
- negotiated protocol: `2025-11-25`
- server identity: `mcp-servers/everything`
- discovered tools: **13**
- missing expected tools: **0**
- deterministic inventory + lock generation: PASS

No discovered tool was executed.

After this first reveal, the Everything dataset is a regression target and must not be described as a future blind holdout.
