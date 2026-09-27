# Examples

`integrations_smoke.py` is the executable reference for embedding KCC into an existing agent stack.

It demonstrates the same two-capability authority surface represented as:

- generic JSON
- MCP tool definitions
- OpenAI function tools
- Anthropic tools
- OpenAPI

Every representation compiles to the same semantic authority and the same task-scoped grant.

Run:

```bash
python examples/integrations_smoke.py
```

Expected terminal marker:

```
KCC_INTEGRATION_RECIPES: PASS
```

The example uses an application-owned dispatcher. No KCC daemon or local control service is required.
