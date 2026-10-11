# 0007. Web app: Next.js server as the only API client, tokens in httpOnly cookies

- **Date:** 2026-10-11
- **Status:** accepted

## Context
Phase 1 needs a learner-facing web app (sign-up, course, lesson player, progress). The API
issues a 15-minute JWT access token and a rotating refresh token with reuse detection
(ADR 0002). Where the browser keeps those tokens decides the app's XSS exposure.

## Options
1. **SPA calling the API directly, tokens in localStorage**: simple, but any injected script
   can read the tokens; needs CORS.
2. **SPA with the API setting httpOnly cookies cross-site**: safe storage, but cross-site
   cookies (different Render domains) need `SameSite=None`, CSRF tokens and CORS credentials.
3. **Next.js server as a backend-for-frontend (BFF)**: the browser only talks to the Next.js
   server; it holds the tokens in its own first-party httpOnly cookies and calls the API
   server-to-server.

## Decision
Option 3, with Next.js 16 (App Router, Cache Components) + TypeScript + Tailwind 4.
- Login/sign-up are Server Actions that call the API and set `httpOnly`, `Secure`,
  `SameSite=Lax` cookies. Browser JavaScript never sees a token; no CORS needed.
- `src/proxy.ts` refreshes the access token shortly before expiry, before pages render
  (Server Components can't set cookies). Concurrent requests share one in-flight refresh, so
  parallel prefetches don't present the same refresh token twice and trip reuse detection.
- Every read goes through `lib/data.ts` → `apiFetch`; every Server Action re-authenticates.
  The proxy is a convenience, not the auth boundary.
- API types are generated from the OpenAPI schema; CI fails if they drift.
- Hosted as a second free Render web service (Frankfurt), declared in `render.yaml`.

## Consequences
- XSS can't exfiltrate tokens; CSRF is covered by `SameSite=Lax` plus Server Actions' origin
  checks.
- Every API call has an extra hop through the Next.js server, and both free services sleep,
  so the first visit after idle is slow.
- The in-memory refresh de-duplication assumes one web instance. With several instances,
  add a short reuse grace period on the API side.
