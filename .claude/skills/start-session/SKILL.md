---
name: start-session
description: Start a Nativly work session - recap where we left off and propose today's goal.
disable-model-invocation: true
argument-hint: "[minutes available, e.g. 45]"
---

Start a work session. Time available: $ARGUMENTS (assume 45 minutes if empty).

1. Read docs/learning/PROGRESS.md. Run `git status` and `git log --oneline -5`.
2. In 2–3 lines: current phase, last thing finished, anything uncommitted or half-done.
3. Propose ONE goal that fits the time and the current phase: what gets built, files that
   change, how it will be verified. Suggest a branch name.
4. Start building once the owner agrees (or immediately if they already said to continue).
