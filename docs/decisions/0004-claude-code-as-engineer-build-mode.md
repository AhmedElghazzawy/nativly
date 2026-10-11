# 0004. Claude Code as the engineer ("build mode")

- **Date:** 2026-10-11
- **Status:** accepted (supersedes [0001](0001-use-claude-code-as-mentor.md))

## Context
ADR 0001 set Claude Code up as a mentor: small chunks, `TODO(human)` handoffs, quizzes. In
practice the owner prefers to learn in a separate Claude chat and wants this repo to move at
a professional pace, with the repo itself as the showcase.

## Options
1. **Keep mentor mode**: maximum learning in the repo, slow delivery.
2. **Build mode**: Claude builds end to end to a defined standard; learning happens elsewhere
   by reading the code, PRs and ADRs.
3. **Hybrid**: per-task switching, which in practice blurs both goals.

## Decision
Option 2. Claude makes routine engineering calls, writes code and tests, and runs the full Git
workflow (branch → PR → green CI → squash-merge). It stops only for product decisions, money,
accounts or the owner's password. Free tiers only; the repo is public, so no secrets ever.
Guard rails stay in place: safety hooks, strict CI, never weakening tests.

## Consequences
- Much faster delivery; PRs and ADRs become the learning material.
- Quality depends on the definition of done in CLAUDE.md and on CI, so both must stay strict.
- Teaching-only tooling (quiz/explain/stuck skills, mentor output style) was removed.
