# Nativly

An AI language school that teaches like a real teacher: adaptive placement, a CEFR curriculum,
a tutor with persistent memory, and real-time speaking practice. English first.

- Full plan: `docs/build-plan.md` (read the relevant phase before planning work)
- Where we are now: @docs/progress/PROGRESS.md
- Why things are the way they are: `docs/decisions/` (ADRs)

---

## 1. How we work

**Claude is the engineer on this repo.** The owner (Ahmed) learns elsewhere; here the goal is a
professional, production-quality product and a repo that reads well to anyone who opens it.

### Autonomy
- Make engineering calls yourself and keep going. Don't stop to ask about routine choices;
  state any non-obvious choice in one line in the final summary.
- Stop and ask **only** for: product decisions, anything that costs money, accounts/sign-ups,
  or something that needs the owner's password.
- Install tools and packages when needed; say in one line what each is for.

### Constraints
- **No paid services.** Use free tiers that need no card (e.g. Neon, Render free). If something
  can only be done with a paid plan, stop and explain the options.
- **The repo is public.** Never commit secrets, real credentials, personal data or `.env` files.
  Secrets live in the host's secret store or a git-ignored `.env`. Never read or print `.env`.
- **Respect the safety hooks** (`.claude/hooks/guard-bash.sh`). If one blocks something, explain
  why it was needed and let the owner run it; never work around a hook.

### Git workflow
- Never commit to `main` directly. One branch per step: `feat/…`, `fix/…`, `chore/…`, `docs/…`.
- Claude commits, pushes, opens the PR (`gh pr create`), waits for CI, fixes failures, and
  **squash-merges once CI is green** (`gh pr merge --squash --delete-branch`), then updates
  local `main`.
- [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `test:`,
  `refactor:`, `docs:`, `chore:`, `ci:`. PR bodies have a Summary and a Test plan.

### Definition of done (every step)
1. Tests written for the new behaviour, including error paths.
2. `pytest --cov`, `ruff check`, `ruff format --check` and `mypy app tests` all pass locally.
3. Docs updated where they changed: README (features, API table, config), this file's
   commands, `PROGRESS.md`, and an ADR for any real choice between alternatives.
4. PR merged with CI green.
5. Session summary appended to `docs/progress/SESSION_LOG.md` (via `/wrap-up`).

### Replies
Short. What changed, why (only when non-obvious), and the verification result. No lesson blocks,
quizzes or `TODO(human)` handoffs.

---

## 2. Product context

- CEFR levels A1–C2, per skill (reading, listening, writing, speaking, grammar, vocab).
- Differentiators: persistent tutor memory, a real curriculum with mastery tracking, teaching
  depth (explain *why*, correct like a teacher). Not gamified, not Duolingo.
- Tagline: "Native gibi konuş."

## 3. Architecture (modular monolith)

One FastAPI codebase split into modules: `auth`, `learning`, `assessment`, `tutor`, `voice`,
`billing`. **No microservices** until something actually hurts.

**AI services layer:** every model call goes through one internal interface
(`llm.complete()`, `stt.transcribe()`, `tts.speak()`) in `api/app/ai/`. Never call a provider
SDK directly from a route or service. This keeps providers swappable, calls logged, cost
tracked per user, and tests runnable with fakes.

```
nativly/
├── api/                FastAPI service (conventions: api/CLAUDE.md)
│   ├── app/
│   │   ├── core/       config.py (Settings) · db.py (Base, engine, get_session) · security.py
│   │   ├── auth/       models · schemas · service · dependencies · router
│   │   ├── learning/   curriculum models · content.py (YAML schema) · importer · router
│   │   ├── models.py   imports every ORM model (for Alembic + tests)
│   │   └── main.py     create_app(): lifespan, CORS, health checks, routers under /api/v1
│   ├── migrations/     Alembic (async env, ruff runs on generated files)
│   ├── tests/          pytest on real Postgres, per-test rollback
│   └── Dockerfile      multi-stage, non-root; build context is the repo root
├── web/                Next.js + TypeScript + Tailwind (Phase 1)
├── content/            curriculum YAML per language/level (rules: content/README.md)
├── infra/              docker-compose.yml (Postgres+pgvector, Redis, migrate job, API)
├── render.yaml         Render Blueprint (free web service; DB on Neon), ADR 0005
├── docs/               build-plan · decisions/ (ADRs) · progress/ (PROGRESS, SESSION_LOG)
└── .github/            CI workflow, Dependabot
```

## 4. Stack

Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 (async, asyncpg) · Alembic · PostgreSQL 16
(pgvector image) · Redis (+ arq later) · PyJWT · pwdlib (Argon2id) · pytest + pytest-asyncio ·
ruff · mypy (strict) · uv · Docker (Colima locally) · GitHub Actions · Next.js (Phase 1) ·
Claude (Sonnet for tutoring, Haiku for grading) behind the AI layer.

## 5. Commands

> Keep this in sync as commands are added. Tests need Postgres running.

```bash
# Infra (repo root). If Docker isn't responding after a reboot: `colima start`
docker compose -f infra/docker-compose.yml up -d                          # Postgres + Redis
docker compose -f infra/docker-compose.yml --profile api up -d --build    # + migrate + API
# Port 8000 may be taken by the owner's other project: prefix with API_PORT=8001

# API (run from api/)
uv sync                                         # install deps
uv run fastapi dev app/main.py                  # dev server, docs at /docs
uv run pytest --cov                             # tests + coverage (fails under 80%)
uv run ruff check . && uv run ruff format .
uv run mypy app tests
uv run alembic upgrade head                     # apply migrations
uv run alembic revision --autogenerate -m "…"   # new migration: always review the file
uv run alembic check                            # models and migrations in sync?
uv run python -m app.learning.importer ../content   # import/refresh curriculum (idempotent)

# GitHub
gh pr create · gh pr checks --watch · gh pr merge --squash --delete-branch
```

## 6. Engineering standards

- **Tests with every feature.** Arrange / act / assert. Test behaviour through the HTTP API
  where possible. Never weaken, skip or delete a test to make it pass. Warnings are errors.
- **Type everything.** mypy strict must pass; no `type: ignore` without a reason.
- **Config from environment** via `Settings` (`NATIVLY_` prefix). Never hard-code secrets.
  A new setting goes in `Settings`, the README config table, and CI/compose if needed.
- **Errors are explicit.** Services raise domain exceptions; routers map them to
  `HTTPException`. No bare `except:`.
- **Comments explain *why*, not *what*.**
- **Dependencies need a reason.** Prefer the stdlib or an existing dependency.
- **If an API might have changed, look it up** (Context7, official docs, `gh api` for action
  versions) instead of guessing. Pin GitHub Actions to tags that actually exist.
- **Record decisions.** Any choice between real alternatives gets an ADR via `/adr`.
- **Security by default:** auth on every protected route, never return internal fields,
  validate and bound all input, least-privilege containers.

## 7. Current milestone

See @docs/progress/PROGRESS.md. **Phase 0 is done** (live at https://nativly-api.onrender.com).
Now Phase 1 (Learning core); read that section of `docs/build-plan.md` before planning.

**Production:** Render service `nativly-api` (`srv-db5nt5navr4c739f84vg`, Frankfurt, free) and
Neon project `nativly-eu` (`spring-credit-38007462`, Frankfurt, Postgres 16). Deploys happen
automatically after CI passes on `main`. Read logs with `render logs -r <service id>`.
Writing secrets to Render is the owner's step (the auto-mode classifier blocks Claude from it):
prepare a script that never prints values and have the owner run it with `!`.

## 8. Slash commands

| Command | Use |
|---|---|
| `/start-session [minutes]` | Recap state, propose and start one goal |
| `/next-step` | Plan the next step from the build plan, then build it |
| `/review [path]` | Review the current diff for bugs, security and design before a PR |
| `/adr <decision>` | Record an architecture decision |
| `/wrap-up` | Verify, update PROGRESS + SESSION_LOG, commit, PR, merge |
