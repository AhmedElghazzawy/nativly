<div align="center">

# Nativly

**An AI language school that teaches like a real teacher.**

*Native gibi konuş.*

**Live API:** [nativly-api.onrender.com/docs](https://nativly-api.onrender.com/docs)

[![CI](https://github.com/AhmedElghazzawy/nativly/actions/workflows/ci.yml/badge.svg)](https://github.com/AhmedElghazzawy/nativly/actions/workflows/ci.yml)
[![API](https://img.shields.io/website?url=https%3A%2F%2Fnativly-api.onrender.com%2Fhealth&label=api&up_message=live)](https://nativly-api.onrender.com/docs)
![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-D7FF64)
![Types: mypy strict](https://img.shields.io/badge/types-mypy%20strict-2A6DB2)

</div>

---

Most language apps gamify vocabulary. Nativly teaches: it places you with an adaptive test,
follows a real CEFR curriculum (A1–C2, per skill), remembers you across sessions, explains
*why* you made a mistake, and lets you practise speaking in real time. English first.

## Features

| | Status |
|---|---|
| Accounts: register, login, JWT access + rotating refresh tokens, `/me` | ✅ |
| Adaptive placement test, per-skill CEFR levels | 🔜 Phase 2 |
| Curriculum: courses, units, lessons, objectives; MCQ, cloze and reorder exercises | ✅ |
| Server-side answer checking, per-objective mastery, lesson progress | ✅ |
| Spaced-repetition vocabulary (FSRS), web lesson player | 🚧 Phase 1 |
| AI tutor with persistent memory of your goals and recurring mistakes | 🔜 Phase 3 |
| Real-time voice tutor with pronunciation feedback | 🔜 Phase 4 |

See the full [build plan](docs/build-plan.md) and [current progress](docs/progress/PROGRESS.md).

## Architecture

A **modular monolith**: one FastAPI service split into domain modules (`auth`, `learning`,
`assessment`, `tutor`, `voice`, `billing`) that can be extracted later if one ever needs to
scale independently. All model calls (LLM, speech-to-text, text-to-speech) go through a single
internal AI layer, so providers stay swappable, calls are logged and cost is tracked per user.

```
┌────────────┐   HTTPS/JSON    ┌───────────────────────────────┐
│  Next.js   │ ──────────────▶ │  FastAPI (async)              │
│  web app   │                 │  auth · learning · tutor · …  │
└────────────┘                 │  └─ ai/ (LLM · STT · TTS)     │
                               └──────┬──────────────┬─────────┘
                                      │              │
                              ┌───────▼──────┐ ┌─────▼──────┐
                              │ PostgreSQL 16│ │   Redis    │
                              │  + pgvector  │ │ cache, jobs│
                              └──────────────┘ └────────────┘
```

**Stack:** Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 (async) · Alembic · PostgreSQL 16
· Redis · pytest · ruff · mypy (strict) · uv · Docker · GitHub Actions · Next.js (soon) ·
Claude behind the AI layer.

## Repository layout

```
nativly/
├── api/                 FastAPI service
│   ├── app/
│   │   ├── core/        settings, database, security primitives
│   │   ├── auth/        users, tokens: models · schemas · service · router
│   │   ├── learning/    curriculum models, YAML importer, curriculum API
│   │   └── main.py      app factory, health checks, router wiring
│   ├── migrations/      Alembic migrations
│   ├── tests/           pytest suite (real Postgres, per-test rollback)
│   └── Dockerfile       multi-stage, non-root production image
├── web/                 Next.js app (Phase 1)
├── content/             curriculum YAML per language and level (see content/README.md)
├── infra/               docker-compose for local development
└── docs/                build plan, architecture decisions (ADRs), progress
```

## Getting started

**Prerequisites:** [uv](https://docs.astral.sh/uv/) and Docker
([Docker Desktop](https://www.docker.com/products/docker-desktop/) or
[Colima](https://github.com/abiosoft/colima)).

```bash
# 1. Start Postgres and Redis
docker compose -f infra/docker-compose.yml up -d

# 2. Install dependencies and apply migrations
cd api
uv sync
uv run alembic upgrade head
uv run python -m app.learning.importer ../content   # load the curriculum

# 3. Run the API with hot reload
uv run fastapi dev app/main.py
```

Open the interactive API docs at <http://localhost:8000/docs>.

To run the production image instead (migrations run automatically first):

```bash
docker compose -f infra/docker-compose.yml --profile api up -d --build
# set API_PORT=8001 if port 8000 is already taken
```

### Configuration

Settings are read from environment variables (or `api/.env`) prefixed with `NATIVLY_`:

| Variable | Default | Notes |
|---|---|---|
| `NATIVLY_ENVIRONMENT` | `local` | `local`, `test`, `staging` or `production` |
| `NATIVLY_DATABASE_URL` | local Compose Postgres | `postgresql+asyncpg://…` |
| `NATIVLY_JWT_SECRET_KEY` | dev-only value | **Required** in staging/production, 32+ chars |
| `NATIVLY_ACCESS_TOKEN_TTL_MINUTES` | `15` | |
| `NATIVLY_REFRESH_TOKEN_TTL_DAYS` | `30` | |
| `NATIVLY_CORS_ORIGINS` | `[]` | JSON list, e.g. `["http://localhost:3000"]` |

Generate a secret with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

## Deployment

Free-tier hosting, no card required ([ADR 0005](docs/decisions/0005-free-tier-hosting-render-and-neon.md)):

- **API:** [Render](https://render.com) web service built from `api/Dockerfile`, declared in
  [`render.yaml`](render.yaml). HTTPS is automatic. It deploys only after CI passes on `main`.
- **Database:** [Neon](https://neon.tech) serverless Postgres 16 in Frankfurt, next to the API (pgvector available).
- **Migrations** run on container start (`api/scripts/start.sh`).
- **Secrets:** Render generates the JWT secret; the Neon URL is set in the Render dashboard.

The free instance sleeps when idle, so the first request after a while can take ~30–60 s.

## API

All application endpoints are versioned under `/api/v1`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness: the process is up |
| `GET` | `/health/ready` | Readiness: the database is reachable (503 if not) |
| `POST` | `/api/v1/auth/register` | Create an account |
| `POST` | `/api/v1/auth/login` | Exchange email + password for a token pair |
| `POST` | `/api/v1/auth/refresh` | Rotate the refresh token, get a new pair |
| `POST` | `/api/v1/auth/logout` | Revoke a refresh token |
| `GET` | `/api/v1/auth/me` | The current user (Bearer token) |
| `GET` | `/api/v1/courses` | Courses (filter with `?language=en&level=A2`) |
| `GET` | `/api/v1/courses/{slug}` | Course outline: units and lessons |
| `GET` | `/api/v1/lessons/{slug}` | A lesson's steps and exercises (answers never included) |
| `POST` | `/api/v1/exercises/{slug}/attempts` | Check an answer; returns the verdict, explanation and updated mastery |
| `POST` | `/api/v1/lessons/{slug}/complete` | Finish a lesson (score = latest attempt per exercise) |
| `GET` | `/api/v1/me/progress` | The learner's lessons and objective mastery, weakest first |

## Development

```bash
cd api
uv run pytest --cov                      # tests + coverage (fails under 80%)
uv run ruff check . && uv run ruff format .
uv run mypy app tests
uv run alembic revision --autogenerate -m "describe change"   # then review the file
```

Every push and pull request runs CI: lint and strict type-check, the test suite against
Postgres, a migration round-trip (`upgrade → check → downgrade → upgrade`), and a Docker build.

### Conventions

- Small branches and PRs (`feat/…`, `fix/…`), [Conventional Commits](https://www.conventionalcommits.org/).
- Each module keeps HTTP (`router.py`), validation (`schemas.py`), persistence (`models.py`)
  and business logic (`service.py`) separate; services have no FastAPI imports.
- Significant technical choices are recorded as [ADRs](docs/decisions/).

## Security

- Passwords hashed with Argon2id; login timing doesn't reveal which emails exist.
- Refresh tokens are stored only as SHA-256 hashes, rotated on every use, and replaying an
  old one revokes all of the user's sessions ([ADR 0002](docs/decisions/0002-auth-jwt-access-and-rotating-refresh-tokens.md)).
- The app refuses to start in staging/production without a strong JWT secret.
- The container runs as a non-root user; Compose binds services to localhost only.
