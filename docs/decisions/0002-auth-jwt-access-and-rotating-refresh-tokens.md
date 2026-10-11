# 0002. Auth: short-lived JWT access tokens + rotating opaque refresh tokens

- **Date:** 2026-10-11
- **Status:** accepted

## Context
The API serves a Next.js web app now and likely a mobile app later. We need stateless request
authentication that scales horizontally, but also the ability to log a user out and to contain
a stolen token.

## Options
1. **Server-side sessions (cookie + session table/Redis)**: simple revocation; every request
   hits the session store; awkward for mobile and for cross-origin APIs.
2. **Long-lived JWT only**: stateless and simple; cannot be revoked before expiry, so a leaked
   token is valid for its whole lifetime.
3. **Short-lived JWT access token + DB-backed refresh token with rotation**: requests stay
   stateless; revocation and theft detection happen at refresh time.

## Decision
Option 3.
- **Access token:** HS256 JWT, 15 minutes, claims `sub`, `type`, `iat`, `exp`. Verified without
  a database lookup for the signature, then the user is loaded to check `is_active`.
- **Refresh token:** 384-bit random opaque string, 30 days. Only its SHA-256 hash is stored
  (`refresh_tokens` table), so a database leak doesn't leak usable tokens.
- **Rotation:** each refresh revokes the presented token and issues a new pair.
- **Reuse detection:** presenting an already-revoked token revokes every active refresh
  token for that user (a replay implies theft).
- **Passwords:** Argon2id via `pwdlib`; login runs a dummy verify for unknown emails so response
  timing doesn't reveal which emails are registered.

## Consequences
- Logout and "log out everywhere" work; access tokens stay valid for up to 15 minutes after.
- The web client must store the refresh token safely (httpOnly cookie via the Next.js
  server is the plan for Phase 1).
- Revisit asymmetric signing (RS256/EdDSA) if other services ever need to verify tokens.
- An expired-token cleanup job is needed once the table grows (arq, Phase 3).
