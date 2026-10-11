# api/ conventions (FastAPI backend)

Loaded when working inside `api/`. The root CLAUDE.md rules still apply. Follow the patterns
in `app/auth/` when adding a module; it is the reference implementation.

## Module layout
Each feature module in `app/<module>/` uses the same files:
- `router.py`: HTTP only. Parse the request, call a service, map domain exceptions to
  `HTTPException`, return a schema. Mounted in `main.py` under `API_PREFIX` (`/api/v1`).
- `schemas.py`: Pydantic v2 request/response models. Bound every string (`max_length`).
  Never return ORM objects or internal fields (e.g. `password_hash`) directly.
- `models.py`: SQLAlchemy 2 ORM models (`Mapped[...]`, `mapped_column`), inheriting
  `app.core.db.Base` (+ `TimestampMixin` when useful). **Register new models in `app/models.py`**
  or Alembic and the tests won't see them.
- `service.py`: business logic and queries. Takes an `AsyncSession`, raises domain exceptions
  (`class XError(Exception)`). No FastAPI imports, so it's testable alone.
- `dependencies.py`: reusable `Annotated[..., Depends(...)]` aliases.
- `repository.py`: only when queries get big enough to deserve their own file.

`app/core/` holds `config.py` (Settings), `db.py` (Base, naming convention, engine, `get_session`)
and `security.py` (password hashing, JWT, refresh tokens). `app/ai/` (Phase 2+) holds the only
code allowed to call LLM/STT/TTS providers.

## Patterns
- Async all the way: `async def` routes, `AsyncSession`, no blocking I/O in a route.
- Inject with the shared aliases: `SessionDep`, `SettingsDep`, `CurrentUser`
  (from `app.auth.dependencies`). Protect a route by adding a `CurrentUser` parameter.
- Settings come from `Depends(get_settings)`, never imported module-level in routes, so tests
  can override them.
- Rely on database constraints for uniqueness (catch `IntegrityError`), not check-then-insert.
- Timestamps are `DateTime(timezone=True)`; use `datetime.now(UTC)` in Python.
- Passwords: `hash_password` / `verify_password` from `app.core.security` (Argon2id). Never log
  or return secrets or tokens.

## Migrations
- Every schema change goes through Alembic: `uv run alembic revision --autogenerate -m "…"`.
- Autogenerate is a draft: read the file, fix what it missed (data migrations, server defaults,
  enum changes), make sure `downgrade()` reverses `upgrade()`.
- Then `alembic upgrade head` and `alembic check` locally. CI also runs a downgrade round-trip.

## Tests
- `tests/` mirrors `app/` (`tests/auth/…`). Test through the HTTP API with the `client` fixture.
- Fixtures in `tests/conftest.py`: `settings`, `engine`, `session` (rolled back after each test),
  `app`, `client`. Use the `session` fixture for direct DB setup/asserts.
- The test DB is `nativly_test` (auto-created; override with `NATIVLY_TEST_DATABASE_URL`).
- External AI providers are always faked in tests.
