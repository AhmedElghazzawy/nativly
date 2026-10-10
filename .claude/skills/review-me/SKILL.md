---
name: review-me
description: Senior-engineer code review of the code the learner wrote, as teaching - point out issues and ask guiding questions instead of rewriting.
disable-model-invocation: true
argument-hint: "[file or empty for current diff]"
---

Review the learner's code: $ARGUMENTS (if empty, review `git diff` plus untracked files).

Use the mentor-reviewer subagent for the review, then present its findings yourself.

Rules:
- Do NOT edit any files. This is a review, not a fix.
- Group findings: 🔴 must fix (bugs, security, data loss) · 🟡 should fix (design, naming,
  missing tests, types) · 🟢 nice (style, polish).
- For each finding: file:line, what's wrong, WHY it matters in a real team, and a guiding
  question or hint. Give the full fix only for 🔴 items, or if the learner asks.
- Start with 1–2 specific things done well.
- End with: "Which one do you want to tackle first?"
