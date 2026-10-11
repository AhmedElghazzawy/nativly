# Nativly progress

**Current phase:** Phase 1 — Learning core
**Next step:** Plan Phase 1: curriculum data model (levels, units, lessons, objectives) + content YAML import.

## Phase 0: Foundation
- [x] Repo layout (api/, web/, content/, infra/, docs/) + README + .gitignore
- [x] `api/`: uv project, FastAPI app, `GET /health`
- [x] Settings class reading environment variables (pydantic-settings)
- [x] First pytest test (health endpoint)
- [x] ruff + mypy configured and passing
- [x] Dockerfile for the API
- [x] docker-compose: Postgres + Redis, API connects to the database
- [x] SQLAlchemy async engine + session dependency
- [x] Alembic set up, first migration
- [x] GitHub Actions CI: ruff, mypy, pytest on every push
- [x] Auth: users table, register, login, JWT access + refresh, `/me`
- [x] Deploy API with HTTPS (free tier: Neon + Render): https://nativly-api.onrender.com
- [x] **Done when:** sign-up works on the live URL and CI is green ✅ 2026-10-11

## Backend v1 checklist (milestone)
- [x] User accounts · [ ] Vocabulary decks · [ ] Spaced repetition review
- [x] OpenAPI docs · [x] Test coverage > 70% · [x] Deployed with HTTPS

## Later phases
1. Learning core · 2. Assessment + writing feedback · 3. AI teacher (text) ·
4. Voice tutor · 5. Personalization + full course · 6–7. see docs/build-plan.md
