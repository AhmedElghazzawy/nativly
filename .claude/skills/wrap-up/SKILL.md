---
name: wrap-up
description: End a work session - make sure everything is tested and understood, update the learning log and PROGRESS.md, and suggest a commit.
disable-model-invocation: true
---

Wrap up this session.

1. Run the tests and linters (`uv run pytest`, `uv run ruff check .`, `uv run mypy app`
   from api/ if they exist yet). Report the result. If anything fails, say so plainly.
2. Ask the learner to explain, in 2–3 sentences, what they built today and the main concept.
   Give feedback on the explanation.
3. Append an entry to docs/learning/LEARNING_LOG.md:

   ```
   ## YYYY-MM-DD — <short title>
   **Built:** ...
   **Concepts:** concept 1, concept 2, ...
   **In my words:** <the learner's explanation from step 2>
   **Struggled with:** ...
   **Next time:** ...
   ```
4. Update docs/learning/PROGRESS.md: tick finished items, set "Next step", and update
   "Review next time".
5. Suggest a conventional commit message (and PR title if the branch is ready). Let the
   learner run the git commands.
