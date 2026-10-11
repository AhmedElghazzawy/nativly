# Learning log

One entry per work session, newest at the bottom. `/wrap-up` writes these.
The "In my words" line is the most important one: if I can't write it, I didn't learn it.

## 2026-10-10 — Project setup
**Built:** Claude Code setup (CLAUDE.md, settings, hooks, skills).
**Concepts:** CLAUDE.md as project memory, hooks, permissions, skills/slash commands.
**In my words:** _(fill in)_
**Struggled with:** —
**Next time:** create the repo skeleton and the `/health` endpoint.

## 2026-10-11 — Phase 0 foundation: API, auth, Docker, CI
**Built:** Repo skeleton; FastAPI app (`/health`, `/health/ready`, `/api/v1` prefix); pydantic
Settings; async SQLAlchemy + Alembic (users, refresh_tokens); auth (register, login, rotating
refresh with reuse detection, logout, `/me`); 27 tests on real Postgres, 94% coverage; multi-stage
Dockerfile; Compose (pgvector Postgres, Redis, migrate job, API); GitHub Actions CI; Dependabot;
README. Switched the repo from mentor mode to build mode.
**Decisions:** ADR 0002 (JWT access + rotating opaque refresh tokens), ADR 0003 (real Postgres
tests with per-test rollback). Colima as the local Docker runtime.
**Next time:** push and get CI green; deploy with HTTPS.

