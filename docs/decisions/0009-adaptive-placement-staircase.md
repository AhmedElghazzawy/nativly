# 0009. Adaptive placement with a per-skill staircase

- **Date:** 2026-10-12
- **Status:** accepted

## Context
New learners need a level per skill and a starting course without a long exam. The build plan
asks for an adaptive test of about 25–35 items. We have no response data yet to calibrate items.

## Options
1. **Fixed test** (same questions for everyone): simple, but long and imprecise at the edges.
2. **Computerized adaptive testing with Item Response Theory** (e.g. 2PL, maximum-information
   item selection): the gold standard, but needs hundreds of responses per item to estimate
   difficulty and discrimination parameters we don't have.
3. **Staircase per skill** (up after right, down after wrong) with items tagged by CEFR level:
   adaptive, explainable, works with an uncalibrated bank, and collects the response data IRT
   needs later.

## Decision
Option 3, as pure functions in `app/placement/staircase.py`.
- Skills: grammar, vocabulary, reading (listening/speaking need audio, later). 6 items each,
  starting at B1, moving one level per answer within A1–B2.
- Level = highest level answered at ≥ 60%. Levels below the lowest one asked count as passed
  (the learner never fell that far). Score 0–100 = accuracy one level up.
- Overall = lower median of skill levels, so one strong skill doesn't over-place a learner;
  the recommended course is the one at that level, or the closest below.
- The server picks every item and only accepts an answer to the pending item, so a test can't
  be skipped, replayed or answered from another account.
- Multiple-choice options are shuffled on import, seeded by slug: our authored bank had the
  answer in position B 56% of the time (lessons: 68%), an exploitable bias.

## Consequences
- Placement is quick (18 items, ~8 minutes) and every result is explainable.
- Precision is limited by 6 items per skill; retakes and practice data will refine levels.
- Every response is stored with its item, so we can move to IRT once there's enough data.
- Next: add the writing task (AI-graded) as a fourth skill, then listening with audio.
