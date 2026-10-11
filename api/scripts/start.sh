#!/bin/sh
# Container entrypoint. Hosts without a separate release step (e.g. Render's free plan) run
# migrations here; Compose runs them in its own `migrate` job and sets RUN_MIGRATIONS=false.
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    alembic upgrade head
fi

# exec so the server becomes PID 1 and receives SIGTERM for graceful shutdown.
exec fastapi run app/main.py --host 0.0.0.0 --port "${PORT:-8000}"
