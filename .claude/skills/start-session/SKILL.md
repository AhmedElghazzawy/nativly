---
name: start-session
description: Start a Nativly work session - recap where we left off, refresh memory with a quick review question, and propose today's small goal.
disable-model-invocation: true
argument-hint: "[minutes available, e.g. 45]"
---

Start a work session. Time available: $ARGUMENTS (assume 45 minutes if empty).

1. Read docs/learning/PROGRESS.md and the last entry of docs/learning/LEARNING_LOG.md.
   Run `git status` and `git log --oneline -5`.
2. In 3–4 lines, recap: current phase, the last thing finished, anything left half-done.
3. Ask ONE spaced-repetition question about something learned in a previous session
   (pick from the "Concepts" lines of older log entries). Wait for the answer, then give
   short feedback.
4. Propose ONE goal that fits the time available and the current phase, with:
   - what we'll build, the concept it teaches, files likely to change, how we'll know it works.
5. Suggest a branch name. Wait for the learner to say "go" before writing any code.
