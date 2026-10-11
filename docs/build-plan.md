# Nativly: full build plan

_Written 2026-10-10. This is a from-scratch plan for an AI language school that teaches like a real teacher: placement, a curriculum, a tutor who remembers you, and real-time speaking practice. It ignores the old roadmap._

---

## 1. Product in one paragraph

A learner signs up, takes an adaptive placement test, and gets a CEFR level for each skill (for example "B1 overall, A2 speaking"). Nativly builds a personal course from that. Every day the learner gets a lesson made of explanation, practice, listening, writing and a speaking session with an AI teacher. The teacher remembers their goals, interests and recurring mistakes, and the course re-plans itself as they improve. English is the first language taught, and the platform is built so that more can be added as content rather than code.

**What makes it different:** persistent memory, a real curriculum with mastery tracking, and teaching depth (explaining *why*, correcting the way a teacher does). Speak, Langotalk, Talkio and SmallTalk2Me each have one or two of these.

---

## 2. Architecture

```
            ┌──────────────────────────── Clients ────────────────────────────┐
            │  Web app (Next.js, PWA)        Mobile later (Expo / React Native) │
            └───────────────┬───────────────────────────┬──────────────────────┘
                     HTTPS / JSON                  WebSocket / WebRTC (voice)
            ┌───────────────▼───────────────────────────▼──────────────────────┐
            │                      API (Python, FastAPI)                         │
            │  auth · users · curriculum · lessons · exercises · SRS · placement │
            │  tutor chat · voice gateway · progress · billing webhooks          │
            └──────┬──────────────┬──────────────┬───────────────┬──────────────┘
                   │              │              │               │
            ┌──────▼─────┐ ┌──────▼─────┐ ┌──────▼──────┐ ┌──────▼────────────────┐
            │ PostgreSQL │ │   Redis    │ │  Workers    │ │  AI services layer     │
            │ + pgvector │ │ cache,     │ │ (arq/Celery)│ │  LLM · STT · TTS ·     │
            │            │ │ queues,    │ │ grading,    │ │  pronunciation scoring │
            │            │ │ rate limit │ │ memory jobs,│ │  (behind one interface)│
            └────────────┘ └────────────┘ │ content gen │ └────────────────────────┘
                                          └─────────────┘
            Object storage (S3/R2): audio, generated media · Observability: Sentry + LLM tracing
```

**Key principle:** it's a modular monolith. One FastAPI codebase is split into clear modules (`auth`, `learning`, `assessment`, `tutor`, `voice`, `billing`). Don't split it into microservices until something actually hurts.

**AI services layer:** every model call goes through one internal interface (`llm.complete()`, `stt.transcribe()`, `tts.speak()`). That lets you swap providers, log every call, track cost per user and write tests with fakes.

---

## 3. Stack and why

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.12 + FastAPI + Pydantic v2 | Best AI ecosystem, async, auto OpenAPI docs |
| ORM / migrations | SQLAlchemy 2 + Alembic | Industry standard, explicit SQL when needed |
| Database | PostgreSQL 16 + pgvector | One DB for relational data and memory embeddings |
| Cache / queue | Redis + arq (or Celery) | Background grading, memory summarization, rate limits |
| Web client | Next.js (React, TypeScript) + Tailwind | One codebase for web and PWA, and good browser audio APIs |
| Mobile (later) | Expo / React Native | Reuses TypeScript and API types. Use SwiftUI only if iOS-only polish matters |
| LLM | Claude (Sonnet for tutoring, Haiku for cheap grading and classification) behind the AI layer | Strong teaching and explanation quality, and the cheap tier handles volume |
| Speech-to-text | Whisper / gpt-4o-transcribe, or Deepgram for streaming | Accurate on accented learner speech, with low-latency streaming |
| Text-to-speech | ElevenLabs (or OpenAI TTS for cheaper bulk) | Natural voice and multiple accents |
| Pronunciation | Azure Pronunciation Assessment | Phoneme-level scores that LLMs can't give reliably |
| Realtime transport | WebSocket first, WebRTC (LiveKit) when latency matters | Simple first, then upgrade |
| Auth | Own JWT + refresh tokens (learn it), or Clerk to save time | — |
| Payments | Stripe | — |
| Infrastructure | Docker, GitHub Actions, Fly.io/Railway first, then AWS (ECS + RDS) | Ship cheaply now and move to AWS as a skill milestone |
| Observability | Sentry, structured logs, Langfuse for LLM traces and cost | You can't improve the tutor without seeing its conversations |

---

## 4. Data model (core tables)

**Users and profile**
- `users`: id, email, password_hash, created_at, locale, timezone
- `learner_profiles`: user_id, target_language, native_language, goals (work, exam, travel), interests[], weekly_minutes, preferred_tutor_style
- `skill_levels`: user_id, skill (reading, listening, writing, speaking, grammar, vocab), cefr_level, score (0–100 within the level), updated_at

**Curriculum (content, language-agnostic)**
- `courses`: language, cefr_level
- `units` → `lessons` → `lesson_steps` (type: explain, exercise, listening, writing, speaking, review)
- `learning_objectives`: id, cefr_level, skill, can_do statement ("can describe past experiences"), grammar_point
- `lesson_objectives`: lesson ↔ objective (many-to-many)
- `exercises`: type (MCQ, cloze, reorder, dictation, free writing, speaking prompt), payload JSON, answer key, objective_id, difficulty

**Progress**
- `objective_mastery`: user_id, objective_id, mastery (0–1), evidence_count, last_seen. **This is the heart of personalization.**
- `lesson_progress`: user_id, lesson_id, status, score, completed_at
- `exercise_attempts`: user_id, exercise_id, response, is_correct, ai_feedback JSON, duration

**Vocabulary and spaced repetition**
- `vocab_items`: lemma, language, cefr_level, definition, examples, audio_url
- `user_cards`: user_id, item_id (vocab *or* a past mistake), FSRS fields (stability, difficulty, due_at), lapses
- `reviews`: card_id, rating, reviewed_at

**Assessment**
- `placement_items`: skill, cefr_level, difficulty (IRT b-parameter later), payload
- `placement_sessions` / `placement_responses`: an adaptive test run plus the result per skill

**Tutor memory**
- `tutor_sessions`: user_id, mode (chat or voice), started_at, summary, topics[]
- `tutor_messages`: session_id, role, content, audio_url, corrections JSON
- `learner_facts`: user_id, fact ("works as a nurse", "has a daughter called Mira", "preparing for IELTS"), source_session, confidence. These are short, editable and always loaded.
- `mistake_log`: user_id, category (grammar point or pronunciation phoneme), example, correction, count, last_seen. This feeds lessons and SRS.
- `memory_chunks`: user_id, text, embedding (vector), created_at. These are session summaries used for semantic recall.

**Billing**
- `subscriptions`, `payments`, `usage_events` (LLM tokens and voice minutes per user, for cost control)

---

## 5. The AI parts, designed

### 5.1 Placement test (adaptive)
- An item bank is tagged by skill and CEFR level. Start at B1, step up on a correct answer and down on a wrong one, and stop when confident. Use about 25–35 items in total.
- Reading, listening, grammar and vocab are auto-scored.
- For writing, the learner gets one prompt. The LLM grades it against a CEFR rubric (range, accuracy, coherence, task) and returns structured JSON with a level and evidence.
- For speaking, there's a 2–3 minute recorded conversation. It goes through STT, then LLM rubric grading plus pronunciation scoring.
- **Calibration:** have 20–50 real learners with known levels (from an IELTS score or a teacher's judgement) take it, then tune the thresholds.

### 5.2 Curriculum engine
- Content is structured as CEFR can-do objectives, then lessons, then exercises. Generate draft content with the LLM, then **review it by hand** (or with a teacher) before it ships. Quality is the moat.
- **Next-lesson selection** (rules first, ML never needed early): pick the objectives with the lowest mastery at the learner's level, weighted by their goals and interests, and include due SRS reviews and recurring mistakes.
- Mastery update: after each attempt, `mastery ← mastery + α·(result − mastery)`. Upgrade to Bayesian Knowledge Tracing later if you want.

### 5.3 AI teacher with memory
For each tutor turn, the context is assembled from:
1. A **system prompt** with the teacher persona, the teaching method (recast errors, ask follow-ups, keep learner talk time high, use their level's vocabulary) and correction rules for this learner.
2. A **profile block** with level per skill, goals and interests, plus the top 20 `learner_facts`.
3. **Current focus**: today's lesson objective and the top 3 recurring mistakes.
4. **Recall**: the top 3 `memory_chunks` by vector similarity to the current topic.
5. The recent messages of this session.

After each session, a background job:
- Writes a session summary and embeds it into `memory_chunks`.
- Extracts new facts and adds them to `learner_facts` (deduplicated, with confidence).
- Extracts corrections and adds them to `mistake_log` and SRS cards.
- Updates `objective_mastery` for the objectives practiced.

Keep the learner in control. A "What my teacher knows about me" page lets them view and delete facts, which matters for trust and for GDPR.

### 5.4 Real-time voice tutor
- **v1, turn-based:** push-to-talk, then STT, then the LLM response streamed, then TTS streamed back. Target about 1.5 seconds to first audio.
- **v2, conversational:** streaming STT with voice activity detection, barge-in (the learner can interrupt) and WebRTC through LiveKit. Target under 800 ms. Consider speech-to-speech realtime models here.
- **Feedback** runs in parallel: the transcript goes to a correction extractor and pronunciation scoring. Show gentle inline corrections after a turn, not mid-sentence, plus a session report at the end.
- **Cost control:** per-user daily voice minutes, Haiku-class models for extraction, cached TTS for fixed lesson audio.

### 5.5 Writing and listening
- **Writing:** an LLM returns structured feedback (corrected text, error list with categories and explanations, a CEFR estimate, one "next time try…" tip). Errors go to `mistake_log`.
- **Listening:** generate scripts at the target level, run TTS with varied voices and accents, and auto-generate comprehension questions. Store the audio once and reuse it.

### 5.6 Evaluation (don't skip this)
- Keep a test set of learner messages and essays with expected corrections and levels. Run it in CI whenever prompts change.
- Track correction precision (don't "correct" right English), level-appropriateness of the tutor's language, and latency and cost per session.

---

## 6. Phases and milestones

Each phase ends with something deployed and usable. The durations assume part-time work of about 10–15 hours a week.

### Phase 0: Foundation (2–3 weeks)
- Monorepo layout: `/api` (FastAPI), `/web` (Next.js), `/infra`. Docker Compose for Postgres and Redis.
- Health endpoint, settings via environment variables, Alembic migrations, pytest, ruff and mypy, GitHub Actions CI.
- Auth: register, login, JWT access and refresh tokens, `/me`.
- Deploy the API and web app to Fly or Railway with HTTPS.

**Done when:** you can sign up on the live site and CI is green on every push.

### Phase 1: Learning core (4–6 weeks)
- Curriculum tables, a seed script and an admin import (YAML/JSON content files).
- Lesson player in the web app: explanation steps plus MCQ, cloze and reorder exercises with instant checking.
- Vocabulary decks plus spaced repetition (FSRS), and a daily review screen.
- Progress dashboard and `objective_mastery` updates.
- Content: hand-build **A2 and B1 English, one unit each** (about 8 lessons).

**Done when:** a learner can do a real lesson and a daily review, and see progress.

### Phase 2: Assessment and writing feedback (3–4 weeks)
- Adaptive placement for grammar, vocab, reading and listening, plus the LLM-graded writing task.
- Writing exercises with structured AI feedback, feeding `mistake_log`.
- The AI services layer, LLM tracing and a first evaluation set.

**Done when:** a new user gets per-skill levels and a starting point in the course.

### Phase 3: AI teacher, text (4–5 weeks)
- Tutor chat with streaming responses, persona and level-aware prompts.
- The memory system: facts, summaries, pgvector recall, mistake extraction and post-session jobs.
- The "What my teacher knows" page.
- The tutor can run a lesson's practice step (role-play tied to the lesson objective).

**Done when:** after three sessions, the tutor naturally references past conversations and drills your recurring mistakes.

### Phase 4: Voice tutor (4–6 weeks)
- v1 push-to-talk voice over WebSocket: STT, LLM, then TTS streaming.
- Speaking placement section and pronunciation scoring.
- Post-session speaking report.
- Usage metering and limits.

**Done when:** you can hold a 10-minute spoken lesson that feels responsive, and get a useful report afterwards.

### Phase 5: Personalization and the full course (ongoing, 4+ weeks)
- The next-lesson engine combining mastery, goals, SRS and mistakes into a daily plan.
- Fill out content from A1 to B2 using LLM generation plus review tooling (an admin review queue).
- Weekly progress emails and streaks done tastefully (not Duolingo-style pressure).
- Voice v2: barge-in and WebRTC.

### Phase 6: Launch (3–4 weeks)
- Landing page, onboarding, pricing, Stripe, a free tier with limits.
- Privacy policy, data export and deletion (GDPR), and abuse limits.
- Closed beta with 20–50 learners and their feedback, then calibrate the placement test.
- Optional move to AWS (ECS, RDS, S3, CloudFront) as an infrastructure milestone.

### Phase 7: Expansion
- C1–C2 content, exam tracks (IELTS, TOEFL), and a mobile app with Expo.
- New target languages (Spanish, German, French): the curriculum is data, so this is mostly content plus voice and STT checks.
- AI-generated grammar videos (script by LLM, then TTS, then slide or avatar rendering).

---

## 7. Costs to watch
- **Voice is the expensive part.** STT, LLM and TTS are charged per minute. Meter from day one and set a free-tier cap.
- Use the cheapest model that passes your evaluation set for each job: the large model only for live tutoring, the small one for grading and extraction.
- Cache everything static, such as lesson audio, listening scripts and generated explanations.

## 8. Biggest risks and how to handle them
| Risk | Mitigation |
|---|---|
| Content quality is weak (AI slop) | Human review queue and a small, excellent course before a big one |
| Tutor corrects wrongly or is too chatty | Evaluation set in CI, strict prompt rules, measured learner talk-time ratio |
| Voice latency feels robotic | Streaming everywhere, measuring time to first audio, WebRTC in v2 |
| Costs explode | Per-user metering, caps, model tiering |
| Scope creep stalls the project | Ship each phase deployed before starting the next |
| Privacy (voice and personal facts) | Learner-visible memory, deletion, regional hosting, no training on user data |

## 9. Repo layout to start with
```
nativly/
├── api/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/        (config, db, security)
│   │   ├── auth/
│   │   ├── learning/    (curriculum, lessons, exercises, srs)
│   │   ├── assessment/
│   │   ├── tutor/       (chat, memory)
│   │   ├── voice/
│   │   └── ai/          (llm, stt, tts adapters)
│   ├── migrations/
│   └── tests/
├── web/                 (Next.js)
├── content/             (curriculum YAML per language/level)
├── infra/               (docker-compose, deploy configs)
└── .github/workflows/
```

## 10. The very first session
1. Create the `nativly` repo with the layout above (empty folders and a README).
2. In `api/`: a FastAPI app with `/health`, a settings class, one pytest test and a Dockerfile.
3. `docker-compose.yml` with Postgres and Redis, and the API connecting to the database.
4. A GitHub Actions workflow that runs ruff and pytest.
