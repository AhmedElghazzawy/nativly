---
name: quiz
description: Quiz the learner on what was built recently, interview-style, to confirm real understanding before moving on.
disable-model-invocation: true
argument-hint: "[topic, or empty for this session's work]"
---

Run a short quiz on: $ARGUMENTS (if empty, on what was built this session; check `git diff`
and recent commits).

- Ask 5 questions, ONE at a time, waiting for each answer.
- Mix: 2 "what does this line do", 1 "what would happen if…", 1 "why did we choose X over Y",
  1 interview-style "explain to me how … works".
- After each answer: say whether it's right, fill the gap in 1–3 sentences, no lecture.
- At the end: a score, the weakest area, and one thing to review. Add any concept they missed
  to the "Review next time" list in docs/learning/PROGRESS.md.
