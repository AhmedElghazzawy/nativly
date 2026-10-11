#!/usr/bin/env bash
# Run every local quality gate: the same checks CI runs, minus the slow e2e job.
#   scripts/check.sh          lint, types, unit/API tests for api/ and web/
#   scripts/check.sh --e2e    also Playwright (needs API on $API_URL and web on :3000)
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"

step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

step "api: ruff"
(cd "$root/api" && uv run ruff check . && uv run ruff format --check .)
step "api: mypy"
(cd "$root/api" && uv run mypy app tests)
step "api: pytest (needs Postgres: docker compose -f infra/docker-compose.yml up -d)"
(cd "$root/api" && uv run pytest -q --cov)

step "web: lint, types, unit tests"
(cd "$root/web" && npm run --silent lint && npm run --silent typecheck && npm test --silent)

if [[ "${1:-}" == "--e2e" ]]; then
  step "web: playwright"
  (cd "$root/web" && npx playwright test)
fi

printf '\n\033[32mAll checks passed.\033[0m\n'
