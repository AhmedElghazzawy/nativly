# Nativly progress

**Current phase:** Phase 0 — Foundation
**Next step:** Push the branch and get CI green on GitHub; then deploy the API with HTTPS (Fly.io or Railway, needs an account).
**Review next time:** _(concepts to revisit; /quiz and /start-session add to this)_

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
- [ ] Deploy API with HTTPS (Fly.io or Railway)
- [ ] **Done when:** sign-up works on the live URL and CI is green

## Backend v1 checklist (milestone)
- [x] User accounts · [ ] Vocabulary decks · [ ] Spaced repetition review
- [x] OpenAPI docs · [ ] Test coverage > 70% · [ ] Deployed with HTTPS

## Later phases
1. Learning core · 2. Assessment + writing feedback · 3. AI teacher (text) ·
4. Voice tutor · 5. Personalization + full course · 6–7. see docs/build-plan.md
