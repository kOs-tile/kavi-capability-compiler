# KAVI Plugin Doctor — Hosted V0

Isolated hosted product surface for Plugin Doctor.

## Architecture

- `frontend/` — Next.js 16.3.8
- `backend/` — FastAPI + pinned KCC v0.1.1
- `vercel.json` — Vercel Services routing and frontend→backend binding

The hosted product does not modify KCC compiler or Guard semantics.

## Current V0

- public GitHub Agent Plugin audit
- remote HTTPS MCP discovery + static readiness audit
- SHIP / FIX / BLOCKED result
- prioritized findings with official-source links when available
- reproducible share links that re-run a public audit rather than storing report data

## Security boundaries

- GitHub input is restricted to repository-root URLs on github.com.
- Remote MCP input must be HTTPS, contain no userinfo, and resolve only to globally routable IP addresses.
- MCP discovery lists tools only. Plugin Doctor never invokes discovered tools.
- Remote MCP query strings are never included in returned report metadata.
- Public-host checks are a V0 SSRF defense; production launch still requires rate limiting and abuse controls.

## Local

Use the current Vercel CLI from this directory:

```bash
vercel dev -L
```

The Services runtime supplies `BACKEND_URL` to the frontend.
