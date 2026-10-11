# Nativly Claude Code setup: install guide

Everything in this folder is ready to copy into the root of the `nativly` repo. It turns
Claude Code into a **mentor that teaches while you build**: learning first, shipping second.

## What's in here

| File | What it does |
|---|---|
| `CLAUDE.md` | Project memory loaded every session. Section 0 is the learning contract: the teaching loop, hard rules, and the modes you can switch with a phrase ("boilerplate mode", "I'll drive", "go deeper"). |
| `api/CLAUDE.md` | FastAPI conventions; loads only when Claude works inside `api/`. |
| `.claude/settings.json` | Shared settings: the mentor output style, permissions (what runs freely, what asks, what's blocked) and hooks. |
| `.claude/output-styles/nativly-mentor.md` | How Claude talks: a "🎓 What you just learned" block after code, "✍️ Your turn" tasks with `TODO(human)`, and a "❓ Quick check" before moving on. |
| `.claude/hooks/session-start.sh` | Every session starts knowing your progress, last log entry and git state. |
| `.claude/hooks/python-quality.sh` | After each Python edit: ruff formats it, and lint problems go back to Claude to fix *and explain*. |
| `.claude/hooks/guard-bash.sh` | Blocks reading `.env`, force-pushes, pushing to main and destructive DB commands. |
| `.claude/skills/*` | Your slash commands (below). |
| `.claude/agents/mentor-reviewer.md` | A read-only senior reviewer used by `/review-me`. |
| `docs/learning/PROGRESS.md` | The Phase 0 and Backend v1 checklists. Claude reads it every session. |
| `docs/learning/LEARNING_LOG.md` | One entry per session, including "In my words". This becomes your evidence of what you know. |
| `docs/decisions/` | Architecture Decision Records (ADRs), with a template and the first one. |
| `docs/build-plan.md` | A copy of the full build plan. |
| `.vscode/` | Recommended extensions and Python/ruff/pytest settings. |
| `gitignore-additions.txt` | Lines to put in `.gitignore` (secrets, venvs, local Claude files). |

## Slash commands

| Command | Use it when |
|---|---|
| `/start-session 45` | You sit down to work (number = minutes you have). Recaps, asks one review question, proposes one goal. |
| `/next-step` | You want the next small step planned, concept first, no code yet. |
| `/explain <file or concept>` | Anything is unclear. `/explain last change` explains the latest diff. |
| `/quiz` | Before moving on. Five questions, one at a time, interview style. |
| `/review-me` | You wrote code and want a senior review. Claude points, you fix. |
| `/stuck <error>` | You're stuck. Hints come one level at a time; say "just show me" to skip ahead. |
| `/adr <decision>` | A real choice comes up (JWT vs sessions, arq vs Celery). |
| `/wrap-up` | End of session: tests, your explanation, learning log, progress, commit message. |

---

## 1. Install the tools (once, on your Mac)

```bash
# Claude Code CLI (skip if you already have it)
curl -fsSL https://claude.ai/install.sh | bash

# Python tooling and the things the hooks need
brew install uv jq gh node
uv python install 3.12
npm install -g pyright          # needed by the pyright-lsp plugin

# Docker Desktop for Postgres/Redis: https://www.docker.com/products/docker-desktop/
gh auth login                   # so Claude can use gh for PRs and CI logs
```

In VS Code, install the extensions it suggests when you open the repo (from `.vscode/extensions.json`),
including **Claude Code** (`anthropic.claude-code`).

## 2. Create the repo and copy the setup in

```bash
mkdir -p ~/dev/nativly && cd ~/dev/nativly
git init -b main
cp -R /path/to/claude-setup/. .        # the trailing /. copies the hidden .claude and .vscode folders too
rm README.md                           # this guide; you'll write the real project README in step 0
cat gitignore-additions.txt >> .gitignore && rm gitignore-additions.txt
chmod +x .claude/hooks/*.sh
```

Then create the GitHub repo and push (you run these, it's your repo):

```bash
git add . && git commit -m "chore: add Claude Code mentor setup"
gh repo create nativly --private --source=. --push
```

## 3. Install the plugins

Open Claude Code in the VS Code terminal (`claude`), then run these one by one.
They come from Anthropic's official marketplace; if it isn't listed under `/plugin`, add it with
`/plugin marketplace add anthropics/claude-plugins-official` first.

**Install now:**

```
/plugin install context7@claude-plugins-official
/plugin install pyright-lsp@claude-plugins-official
/plugin install security-guidance@claude-plugins-official
/plugin install pr-review-toolkit@claude-plugins-official
/plugin install claude-md-management@claude-plugins-official
```

| Plugin | Why it's here |
|---|---|
| **context7** | Pulls current docs for FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, so Claude teaches you today's API, not a 2023 one. Ask "use context7" when in doubt. |
| **pyright-lsp** | Gives Claude real type-checking and go-to-definition, so it catches type errors as it writes and can explain them. |
| **security-guidance** | Warns on insecure patterns as code is written (secrets, injection) and reviews diffs. Every warning is a free security lesson. |
| **pr-review-toolkit** | Specialised reviewers for your PRs: tests, error handling, type design. Run it before you merge, like a real team review. |
| **claude-md-management** | Keeps CLAUDE.md accurate as the project grows (audits it, captures new conventions). |

**Add later, when the phase needs it:**

| When | Plugin | Why |
|---|---|---|
| Phase 0 end / Phase 1 (web app) | `typescript-lsp`, `playwright` | TypeScript intelligence; Playwright lets Claude open the web app and test it in a browser. |
| Phase 2+ (deployed, real users) | `sentry` | Read production errors with Claude. |
| Billing phase | `stripe` | Stripe integration help. |

**Deliberately skipped:**
- `learning-output-style` / `explanatory-output-style`: Claude Code now has these built in, and
  the custom Nativly Mentor style already does this job. Installing them would stack conflicting instructions.
- `feature-dev`, `superpowers`, `ralph-wiggum` and similar autopilot plugins: they build whole features
  autonomously, which is the opposite of the learning goal. Maybe after Backend v1.
- `commit-commands` and the `github` plugin: you run git yourself while learning, and `gh` covers the rest without a token.

## 4. MCP servers

- **Context7** comes with the plugin above. Nothing else to do.
- **GitHub**: use the `gh` CLI (installed in step 1). Claude uses it for PRs, issues and CI logs.
- **Postgres** (add once docker-compose is running in Phase 0). It lets Claude inspect your real
  schema and explain query plans. Restricted mode = read-only:

  ```bash
  claude mcp add postgres -e DATABASE_URI=postgresql://nativly:nativly@localhost:5432/nativly \
    -- uvx postgres-mcp --access-mode=restricted
  ```
  Use your real local credentials from `.env`. This is saved to your local (personal) scope, not committed.

- **Playwright**: comes with the plugin when you reach the web app.

## 5. Check it works

Inside `claude`:

1. The first message should show the "Nativly session context" (from the SessionStart hook).
2. `/output-style` should show **Nativly Mentor** selected.
3. `/hooks` lists the three hooks; `/memory` shows CLAUDE.md and PROGRESS.md loaded.
4. Type `/` and you should see `start-session`, `next-step`, `wrap-up` and the others.
5. Run `/ide` once so Claude's edits open as diffs in VS Code.

If a hook doesn't fire, check `chmod +x .claude/hooks/*.sh` and that `jq` is installed.

## 6. A normal session

```
/start-session 60        → recap, a review question, today's goal
"go"                     → Claude plans, writes scaffolding, explains it, leaves TODO(human) for you
(you write your part)    → "done" → Claude reviews it, then a quick-check question
/quiz  or  /explain ...  → whenever you're not 100% sure
/wrap-up                 → tests, your explanation, log + progress updated, commit message
git commit / push        → you do this
```

Your first `/start-session` will propose Step 0 from the build plan: the repo skeleton and a
`/health` endpoint with its first test.

## Making it yours

- Personal preferences that shouldn't be committed go in `CLAUDE.local.md` (git-ignored).
- Change permissions or hooks by asking Claude to "update the settings", or edit `.claude/settings.json`.
- If the explanations feel too long or too short, tell Claude, then use `/wrap-up` to record it,
  or edit the output style file.
