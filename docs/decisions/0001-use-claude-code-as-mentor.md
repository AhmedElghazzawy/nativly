# 0001. Build Nativly with Claude Code as a mentor, not an autopilot

- **Date:** 2026-10-10
- **Status:** accepted

## Context
Nativly's first goal is learning professional software engineering; shipping is second.
AI tools can generate most of this code, which would ship faster but teach little.

## Options
1. **Autopilot:** let Claude write features end to end. Fast, but I couldn't defend the code in an interview.
2. **No AI:** write everything alone. Slow, and no senior feedback.
3. **Mentor mode:** Claude explains, plans and writes boilerplate; I write the code that teaches; nothing moves on until I understand it.

## Decision
Mentor mode (3), enforced through CLAUDE.md, the Nativly Mentor output style, hooks and the
learning skills (/next-step, /explain, /quiz, /review-me, /stuck, /wrap-up).

## Consequences
Progress is slower per feature. In exchange, every line is mine to explain, and the learning
log becomes evidence of what I know.
