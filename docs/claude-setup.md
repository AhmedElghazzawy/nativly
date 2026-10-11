# Claude Code setup

How this repo is configured for [Claude Code](https://claude.com/claude-code), which builds
Nativly in "build mode" ([ADR 0004](decisions/0004-claude-code-as-engineer-build-mode.md)).

| File | Purpose |
|---|---|
| `CLAUDE.md` | Project memory loaded every session: how we work, architecture, commands, standards. |
| `api/CLAUDE.md` | Backend conventions; loaded when working in `api/`. |
| `.claude/settings.json` | Shared permissions (what runs freely, what asks, what's blocked) and hooks. |
| `.claude/hooks/session-start.sh` | Starts each session with current progress, the last session log entry and git state. |
| `.claude/hooks/python-quality.sh` | After every Python edit: ruff formats the file and lint errors must be fixed immediately. |
| `.claude/hooks/guard-bash.sh` | Blocks reading `.env`, force-pushes, pushing to `main` and destructive DB commands. |
| `.claude/skills/` | Slash commands: `/start-session`, `/next-step`, `/review`, `/adr`, `/wrap-up`. |
| `.claude/agents/code-reviewer.md` | Read-only reviewer used by `/review` before a PR. |
| `docs/progress/` | `PROGRESS.md` (phase checklists) and `SESSION_LOG.md` (one entry per session). |

## Local tooling

```bash
brew install uv jq gh node colima docker docker-compose docker-buildx
uv python install 3.12
npm install -g pyright          # for the pyright-lsp plugin
colima start                    # Docker runtime (no Docker Desktop needed)
gh auth login
```

Recommended plugins (from `claude-plugins-official`): `context7` (current library docs),
`pyright-lsp` (type intelligence), `security-guidance`, `pr-review-toolkit`.

## Personal overrides

`CLAUDE.local.md` and `.claude/settings.local.json` are git-ignored for personal preferences.
