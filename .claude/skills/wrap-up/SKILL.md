---
name: wrap-up
description: End a work session - verify everything passes, update PROGRESS.md and the session log, and suggest a commit.
disable-model-invocation: true
---

Wrap up this session.

1. From api/: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`,
   `uv run mypy app tests`. Report results plainly; fix failures before continuing.
2. Append a short entry to docs/learning/LEARNING_LOG.md:

   ```
   ## YYYY-MM-DD — <short title>
   **Built:** ...
   **Decisions:** ... (link ADRs if any)
   **Next time:** ...
   ```
3. Update docs/learning/PROGRESS.md: tick finished items and set "Next step".
4. Suggest a branch name (if still on main), a conventional commit message, and a PR title
   if the branch is ready. The owner runs the git commands.
