#!/usr/bin/env bash
# Runs after Claude edits or writes a file. For Python files it formats the file with
# ruff, then lints it. Lint problems are reported back to Claude (exit 2) so it has to
# fix them AND explain the rule to the learner, instead of the problems piling up.
input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
case "$file" in *.py) ;; *) exit 0 ;; esac
[ -f "$file" ] || exit 0

if command -v ruff >/dev/null 2>&1; then RUFF="ruff"
elif command -v uvx >/dev/null 2>&1; then RUFF="uvx ruff"
else exit 0
fi

$RUFF format --quiet "$file" >/dev/null 2>&1
if ! out=$($RUFF check "$file" 2>&1); then
  {
    echo "ruff found issues in $file:"
    echo "$out"
    echo "Fix them, and briefly explain to the learner what each rule protects against."
  } >&2
  exit 2
fi
exit 0
