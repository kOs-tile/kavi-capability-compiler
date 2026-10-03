# KAVI Plugin Doctor — Deployment Runbook

Status: hosted V0 candidate

## Canonical source

- Repository: `kOs-tile/kavi-capability-compiler`
- Incubation parent: `product/plugin-doctor-v0`
- Hosted branch: `product/plugin-doctor-web-v0`
- App root: `apps/plugin-doctor-hosted`

This is temporary incubation topology. The durable target remains a standalone
`kavi-plugin-doctor` repository pinned to a stable KCC release.

## Dedicated Vercel project

Create a new Vercel project named:

`kavi-plugin-doctor`

Do not recycle unrelated preview/diagnostic projects.

Connect the canonical GitHub source and set the project root to:

`apps/plugin-doctor-hosted`

The repository contains a Vercel Services configuration with:

- `frontend`: Next.js
- `backend`: FastAPI
- same-origin `/api/*` routing to the backend

## Environment

### Required before meaningful public load

`GITHUB_TOKEN`

Use a narrowly scoped credential suitable for reading public repository
metadata/content through the GitHub API. Keep it only in Vercel encrypted
environment configuration. Never expose it to the frontend.

Without a token, public GitHub audits can still work but inherit GitHub's
lower unauthenticated rate budget.

### Remote MCP

`ENABLE_REMOTE_MCP` is intentionally OFF by default.

Do not enable it on the public deployment until outbound egress / DNS-rebinding
controls are strong enough to treat arbitrary user-supplied MCP URLs as hostile.

The backend already rejects:

- non-HTTPS targets
- localhost
- private, loopback, link-local, reserved and other non-global addresses
- userinfo credentials
- query strings
- fragments

KCC/httpx2 discovery does not follow redirects by default when using the current
custom client path, but DNS rebinding remains part of the public-host threat model.

## Production smoke gate

Before promoting a preview deployment:

1. `GET /api/health` returns `ok: true`.
2. Home page renders.
3. Public GitHub dogfood repo returns `SHIP / 100 / 0 blockers` under the current V0 rules.
4. Malformed/unsafe inputs fail closed.
5. Oversized request body returns 413.
6. Hosted MCP request returns 503 while the feature flag is disabled.
7. Response headers include `Cache-Control: no-store`.
8. Browser mobile + desktop interaction passes.
9. Runtime logs show no unexpected 5xx errors.
10. Vercel Firewall/rate controls are configured before broad public promotion.

## Current public dogfood target

`https://github.com/AvdLee/Swift-Concurrency-Agent-Skill`

The observed score is a structural/readiness V0 result only. It is not an
OpenAI approval, ranking, distribution, or security guarantee.

## Vercel account cleanup

Delete after authenticated dashboard access is available:

- `kavi-r3f-diagnostic`
- `kavi-r3f-director-preview`
- `kavi-r3f-director-preview-v2`
- `kavi-r3f-director-temp-public`

Keep:

- `pulse-fitness-baraboo-staging`
- `kavi-photo-story-live`
- `kavi-dispatch-bridge`

After cleanup, re-list Vercel projects and verify the four temporary projects
are absent before considering the cleanup complete.


## Preview integration checkpoint

A branch push on `product/plugin-doctor-web-v0` is used to verify the dedicated
Vercel Git integration and preview deployment path before production promotion.
