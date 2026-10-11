# Nativly

An AI language school that teaches like a real teacher: adaptive placement, a CEFR curriculum,
a tutor with persistent memory, and real-time speaking practice. English first.
Full plan: docs/build-plan.md (read the relevant phase when planning) · Where we are now: @docs/learning/PROGRESS.md

---

## 0. How we work: build mode

Teaching happens outside this repo (in a separate Claude chat). **Here, Claude is the engineer:**
build Nativly to a professional, production-quality standard.

- Write complete, working code. No `TODO(human)` handoffs, no quizzes, no lesson blocks.
- Keep replies short: what changed, why (only when non-obvious), and the verification result.
- Work in small, reviewable steps that match the current phase in PROGRESS.md.
- Stop and ask only for real product/architecture decisions; record those as ADRs (`/adr`).
- Always verify: tests, ruff and mypy pass before calling a step done.
- **Never weaken, skip or delete a test to make it pass.**
- **No dependency without a reason**: state in one line what it does and why.
- **Git:** suggest branch names and commit messages; the owner runs `git commit`, `push` and merges
  unless they explicitly ask otherwise.
- If an API might have changed, look it up (Context7) instead of guessing.
- Push back on anything insecure, over-engineered or out of phase.

### Sizing to the owner's life

GPA and the capstone (ai-ticket-assistant) come first. Assume short sessions. Every session
should end with something committed and working, even if small. Prefer finishing a tiny step
over half-finishing a big one.

---

## 1. Product context

- CEFR levels A1–C2, per skill (reading, listening, writing, speaking, grammar, vocab).
- Differentiators: persistent tutor memory, a real curriculum with mastery tracking, teaching
  depth (explain *why*, correct like a teacher). Not gamified, not Duolingo.
- Tagline: "Native gibi konuş."

## 2. Architecture (modular monolith)

One FastAPI codebase split into modules: `auth`, `learning`, `assessment`, `tutor`, `voice`,
`billing`. **No microservices** until something actually hurts.

**AI services layer:** every model call goes through one internal interface
(`llm.complete()`, `stt.transcribe()`, `tts.speak()`) in `api/app/ai/`. Never call a provider
SDK directly from a route or service. This keeps providers swappable, calls logged, cost
tracked per user, and tests runnable with fakes.

```
nativly/
├── api/            FastAPI app (see api/CLAUDE.md)
│   ├── app/        main.py, core/, auth/, learning/, assessment/, tutor/, voice/, ai/
│   ├── migrations/ Alembic
│   └── tests/
├── web/            Next.js + TypeScript + Tailwind (Phase 0 end / Phase 1)
├── content/        curriculum YAML per language/level
├── infra/          docker-compose, deploy configs
└── docs/           build plan, learning log, decisions (ADRs)
```

## 3. Stack

Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 (async) · Alembic · PostgreSQL 16 (+pgvector
later) · Redis + arq · pytest · ruff · mypy · uv (package manager) · Docker Compose ·
GitHub Actions · Next.js (later) · Claude (Sonnet for tutoring, Haiku for grading) behind the AI layer.

## 4. Commands

> Keep this in sync as commands are added. Tests need Postgres running (compose below).

```bash
# API (run from api/)
uv sync                          # install deps
uv run fastapi dev app/main.py   # dev server, docs at http://localhost:8000/docs
uv run pytest                    # tests
uv run pytest --cov              # coverage (fails under 80%)
uv run ruff check . && uv run ruff format .
uv run mypy app tests
uv run alembic upgrade head      # apply migrations

# Infra (repo root)
docker compose -f infra/docker-compose.yml up -d   # Postgres + Redis
docker compose -f infra/docker-compose.yml --profile api up -d --build   # + API container
```

## 5. Engineering standards

- **Small steps, small PRs.** One branch per step: `feat/health-endpoint`, `fix/...`.
  Conventional commits: `feat:`, `fix:`, `test:`, `refactor:`, `docs:`, `chore:`.
- **Tests with every feature.** Arrange / act / assert. Test behaviour through the HTTP API
  where possible.
- **Type everything.** Full type hints; mypy must pass.
- **Config from environment** via a Pydantic `Settings` class. Secrets only in `.env`
  (git-ignored). Never hard-code keys, never print them, never read `.env` files.
- **Errors are explicit.** Raise `HTTPException` (or domain exceptions mapped to HTTP) with
  clear messages. No bare `except:`.
- **Comments explain *why*, not *what*.** The learning explanations go in the conversation and
  the learning log, not as noise in the code.
- **Record decisions.** Any choice between real alternatives (JWT vs sessions, arq vs Celery,
  FSRS vs SM-2) gets an ADR in `docs/decisions/` via `/adr`.

## 6. Current milestone

See @docs/learning/PROGRESS.md. Phase 0 (Foundation): repo, `/health`, settings, Postgres +
Redis in Compose, Alembic, pytest/ruff/mypy, CI, auth (register/login/JWT/refresh/`/me`),
deployed with HTTPS. **Don't build Phase 1+ features until Phase 0 is done and deployed.**

## 7. Slash commands in this repo

`/start-session` · `/next-step` · `/explain <file|concept>` · `/quiz` · `/review-me` ·
`/stuck` · `/adr <decision>` · `/wrap-up`
