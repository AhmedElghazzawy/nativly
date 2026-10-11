# 0003. Test against real Postgres with per-test transaction rollback

- **Date:** 2026-10-11
- **Status:** accepted

## Context
The app depends on Postgres behaviour (unique constraints, `FOR UPDATE`, timezone-aware
timestamps, and later pgvector). Tests must be fast, isolated and trustworthy.

## Options
1. **SQLite in memory**: fast and zero setup, but different SQL dialect and no pgvector;
   tests can pass while production fails.
2. **Real Postgres, recreate schema per test**: accurate, but slow.
3. **Real Postgres, schema once per run, each test in a rolled-back transaction**: accurate
   and fast.

## Decision
Option 3. A `nativly_test` database is created automatically, the schema is built once per
session from the ORM metadata, and each test runs in an outer transaction; app-level commits
become savepoints (`join_transaction_mode="create_savepoint"`) and everything is rolled back.
CI separately checks that Alembic migrations apply, match the models (`alembic check`) and
reverse cleanly. Local Postgres/Redis run in Docker Compose using the `pgvector/pgvector:pg16`
image so embeddings need no migration later.

## Consequences
- Tests need Docker running locally (`docker compose -f infra/docker-compose.yml up -d`).
- Code that opens its own sessions outside the `get_session` dependency won't share the test
  transaction; keep database access behind that dependency.
