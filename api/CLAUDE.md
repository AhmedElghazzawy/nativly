# api/ conventions (FastAPI backend)

Loaded when working inside api/. The root CLAUDE.md teaching rules still apply.

## Module layout
Each feature module in `app/<module>/` uses the same files:
- `router.py`: HTTP layer only. Parse the request, call a service, return a schema.
- `schemas.py`: Pydantic v2 request/response models. Never return ORM objects directly.
- `models.py`: SQLAlchemy 2 ORM models (`Mapped[...]`, `mapped_column`).
- `service.py`: business logic. No FastAPI imports here, so it's testable alone.
- `repository.py` (when queries grow): database access.

`app/core/` holds `config.py` (Settings), `db.py` (engine, session dependency) and
`security.py` (hashing, JWT). `app/ai/` holds the only code allowed to call LLM/STT/TTS providers.

## Patterns
- Async all the way: `async def` routes, `AsyncSession`, never call blocking I/O in a route.
- Dependencies via `Depends()` (DB session, current user, settings).
- Every schema change goes through an Alembic migration. Explain the generated migration
  to the learner before applying it; autogenerate is a draft, not the truth.
- Passwords hashed with a slow hash (argon2/bcrypt). Never log or return secrets.

## Tests
- `tests/` mirrors `app/`. Use `httpx.AsyncClient` against the app for API tests.
- Tests use a separate test database and roll back between tests.
- External AI providers are always faked in tests.
