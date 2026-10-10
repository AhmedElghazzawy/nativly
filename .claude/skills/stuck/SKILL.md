---
name: stuck
description: Help when the learner is stuck - graduated hints from a nudge to the full answer, debugging the problem together.
disable-model-invocation: true
argument-hint: "[what you're stuck on / the error]"
---

The learner is stuck on: $ARGUMENTS

Use a hint ladder. Give ONE level at a time and wait between levels:

1. **Clarify**: ask what they expected vs what happened, and what they've tried.
2. **Point**: name the area (file, function, concept) where the problem lives.
3. **Nudge**: a guiding question or the relevant doc/concept.
4. **Show the shape**: pseudocode or the first line of the fix.
5. **Answer**: the full fix, explained line by line.

If there's an error, first read the traceback together: what the error type means, which
frame is ours vs the library's, and the line that matters. Teach how to debug, not just the fix.
If they say "just show me", jump to level 5 but still explain.
