#!/usr/bin/env bash
# Runs before every Bash command Claude wants to run. Exit code 2 blocks the command and
# the message on stderr is shown to Claude. This is a safety net on top of the
# permission rules in settings.json, for patterns those rules can't express.
input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)
[ -z "$cmd" ] && exit 0

block() { echo "Blocked by .claude/hooks/guard-bash.sh: $1" >&2; exit 2; }

# Secrets: never print env files or keys into the conversation.
if printf '%s' "$cmd" | grep -Ev '\.env\.example' | grep -Eq '(cat|less|more|head|tail|bat)[^|;&]*\.env'; then
  block "don't read .env files. Ask the owner to check the value themselves."
fi
# History rewriting on shared branches.
if printf '%s' "$cmd" | grep -Eq 'git push.*(--force|-f( |$))'; then
  block "force-push is never done by Claude in this repo."
fi
if printf '%s' "$cmd" | grep -Eq 'git push.*[ :](main|master)( |$)'; then
  block "work on a feature branch, not main. Create a feature branch and open a PR instead."
fi
# Destructive database commands.
if printf '%s' "$cmd" | grep -Eiq '(drop (database|table)|alembic downgrade base|docker compose down -v)'; then
  block "destructive database command. Explain what it would do and let the owner run it."
fi
exit 0
