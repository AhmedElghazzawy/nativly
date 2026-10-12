# Nativly progress

**Current phase:** Phase 1 done → Phase 2 — Assessment and writing feedback
**Next step:** Configure the production Gemini key (owner), then Phase 3: the AI teacher (text) with memory.

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

## Phase 1: Learning core
- [x] Curriculum tables (courses, units, lessons, steps, objectives, exercises) + migration
- [x] YAML content format, validator and idempotent importer (runs on deploy)
- [x] Curriculum API: courses, course outline, lesson with public exercises
- [x] Content: A2 Unit 1 "Talking about the past", lessons 1–2
- [x] Exercise attempts + server-side checking + `objective_mastery` + lesson progress
- [x] Vocabulary decks + FSRS spaced repetition + daily review API (ADR 0008)
- [x] Progress API (`/me/progress`); richer dashboard stats later
- [x] Web app (Next.js): sign-up/login, course outline, lesson player, progress (+ e2e tests)
- [x] Web: word decks, daily review (keyboard-friendly), today banner, streaks
- [x] Content: A1, A2 and B1 Unit 1 — 12 lessons, 60 exercises, 3 decks / 90 words
- [x] Web: level picker + per-course outline with level tabs (remembers the learner's course)
- [x] **Done when:** a learner can do a real lesson and a daily review, and see progress ✅ 2026-10-11

## Phase 2: Assessment and writing feedback
- [x] AI services layer: `LLM.complete()`, Gemini + fake/demo providers, quotas, `llm_calls` log
- [x] Writing tasks in lessons + AI feedback (corrections, explanations, CEFR, scores) + mistake log
- [x] Web: writing step with live word count, marked-up corrections, recurring mistakes on Progress
- [ ] Production Gemini key configured (owner: create key in AI Studio, run the setup script)
- [x] Adaptive placement test (grammar, vocab, reading) → per-skill levels + recommended course (ADR 0009)
- [x] MCQ option shuffling on import (removes measured answer-position bias)
- [ ] Placement: add the AI-graded writing task as a fourth skill
- [ ] Evaluation set for writing feedback (expected corrections; run when prompts change)
- [x] **Done when:** a new user gets per-skill levels and a starting point in the course ✅ 2026-10-12

## Backend v1 checklist (milestone)
- [x] User accounts · [ ] Vocabulary decks · [ ] Spaced repetition review
- [x] OpenAPI docs · [x] Test coverage > 70% · [x] Deployed with HTTPS

## Later phases
1. Learning core · 2. Assessment + writing feedback · 3. AI teacher (text) ·
4. Voice tutor · 5. Personalization + full course · 6–7. see docs/build-plan.md
