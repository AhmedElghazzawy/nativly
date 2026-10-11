# 0008. FSRS for spaced repetition

- **Date:** 2026-10-11
- **Status:** accepted

## Context
Vocabulary (and later, recurring mistakes) must come back right before the learner would
forget them. The scheduler decides how many reviews a learner does per word, which is the
biggest lever on both retention and daily workload.

## Options
1. **SM-2** (SuperMemo 1987, Anki's legacy default): simple, well known; fixed ease factors,
   no model of forgetting, tends to over- or under-review.
2. **Leitner boxes**: trivial to implement, crude intervals.
3. **FSRS** (Free Spaced Repetition Scheduler, Anki's default since 23.10): models memory
   stability, difficulty and retrievability; in published benchmarks it reaches the same
   retention with noticeably fewer reviews than SM-2; parameters can be optimized per learner
   from their review history.

## Decision
FSRS 6 via the maintained reference library `py-fsrs`, isolated behind `app/vocab/srs.py`.
- Target retention 90%; fuzzed due dates so words learned together don't return together;
  un-fuzzed previews for the interval shown on each rating button.
- Every review is logged (`reviews`), so per-learner parameter optimization can be added later
  without changing the schema.
- Daily queue: due cards first, then up to `new_cards_per_day` (10) new words from decks the
  learner studies, counted in the learner's local day (IANA timezone from the browser).
- Learning cards due within 20 minutes count as due ("learn ahead"), so a failed word returns
  in the same session.
- "Mature" = stability of 21 days or more (Anki's convention), shown as "known".

## Consequences
- Better retention per minute studied; a credible, explainable algorithm.
- A dependency on `py-fsrs`; contained to one module, so swapping or forking is cheap.
- Next: feed `mistake_log` entries into the same card system (build plan §5.3).
