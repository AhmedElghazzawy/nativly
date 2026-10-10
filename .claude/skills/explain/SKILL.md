---
name: explain
description: Explain a file, function, diff or concept line by line at the learner's level, then check understanding.
disable-model-invocation: true
argument-hint: "<file path | function | concept | 'last change'>"
---

Explain: $ARGUMENTS

- If it's a file or function: read it, then walk through it in order, in chunks of a few
  lines. For each chunk: what it does, why it's written this way, what would break if it
  were removed, and the common alternative.
- If it's "last change": use `git diff` (or `git diff HEAD~1`) and explain the change.
- If it's a concept: plain definition → a tiny example → where it appears in Nativly →
  a common misconception.
- Draw an ASCII diagram when a flow is involved (request lifecycle, auth flow, data model).
- Finish with two check questions of increasing difficulty. Wait for answers.
