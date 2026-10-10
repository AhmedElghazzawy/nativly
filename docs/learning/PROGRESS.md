# Nativly progress

**Current phase:** Phase 0 — Foundation
**Next step:** Create the repo skeleton: README, .gitignore, folder layout, `api/` with uv.
**Review next time:** _(concepts to revisit; /quiz and /start-session add to this)_

## Phase 0: Foundation
- [ ] Repo layout (api/, web/, content/, infra/, docs/) + README + .gitignore
- [ ] `api/`: uv project, FastAPI app, `GET /health`
- [ ] Settings class reading environment variables (pydantic-settings)
- [ ] First pytest test (health endpoint), written by me
- [ ] ruff + mypy configured and passing
- [ ] Dockerfile for the API
- [ ] docker-compose: Postgres + Redis, API connects to the database
- [ ] SQLAlchemy async engine + session dependency
- [ ] Alembic set up, first migration
- [ ] GitHub Actions CI: ruff, mypy, pytest on every push
- [ ] Auth: users table, register, login, JWT access + refresh, `/me`
- [ ] Deploy API with HTTPS (Fly.io or Railway)
- [ ] **Done when:** sign-up works on the live URL and CI is green

## Backend v1 checklist (milestone)
- [ ] User accounts · [ ] Vocabulary decks · [ ] Spaced repetition review
- [ ] OpenAPI docs · [ ] Test coverage > 70% · [ ] Deployed with HTTPS

## Later phases
1. Learning core · 2. Assessment + writing feedback · 3. AI teacher (text) ·
4. Voice tutor · 5. Personalization + full course · 6–7. see docs/build-plan.md
