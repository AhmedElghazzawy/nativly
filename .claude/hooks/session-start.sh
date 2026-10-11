#!/usr/bin/env bash
# Runs at the start of every Claude Code session. Whatever this prints is added to
# Claude's context, so each session starts knowing where the last session left off.
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

echo "=== Nativly session context ==="
echo "Build mode: Claude is the engineer here (see CLAUDE.md section 0)."

if [ -f docs/progress/PROGRESS.md ]; then
  echo
  echo "--- Current progress (docs/progress/PROGRESS.md, first 40 lines) ---"
  head -n 40 docs/progress/PROGRESS.md
fi

if [ -f docs/progress/SESSION_LOG.md ]; then
  echo
  echo "--- Most recent session-log entry ---"
  # Print from the last "## " heading to the end of the file.
  awk '/^## /{buf=""} {buf=buf $0 "\n"} END{printf "%s", buf}' docs/progress/SESSION_LOG.md | head -n 30
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo
  echo "--- Git ---"
  echo "Branch: $(git branch --show-current)"
  git status --short | head -n 20
  echo "Last commits:"
  git log --oneline -5 2>/dev/null
fi
exit 0
