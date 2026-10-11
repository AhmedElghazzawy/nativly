---
name: wrap-up
description: End a work session - verify, update PROGRESS.md and the session log, then commit, open a PR and merge when CI is green.
disable-model-invocation: true
---

Wrap up this session.

1. From api/: `uv run pytest --cov`, `uv run ruff check .`, `uv run ruff format --check .`,
   `uv run mypy app tests`. Fix failures before continuing.
2. Append a short entry to docs/progress/SESSION_LOG.md:

   ```
   ## YYYY-MM-DD — <short title>
   **Built:** ...
   **Decisions:** ... (link ADRs if any)
   **Next time:** ...
   ```
3. Update docs/progress/PROGRESS.md: tick finished items and set "Next step".
4. Commit on the feature branch (conventional message), push, open the PR, wait for CI,
   fix any failure, squash-merge, and update local `main`.
5. Report: what shipped, the PR link, and the next step.
