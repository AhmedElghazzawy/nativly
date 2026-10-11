from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

_INSECURE_DEV_SECRET = "insecure-local-dev-only-secret-0000"  # noqa: S105 - local-only fallback
_LOCAL_DATABASE_URL = "postgresql+asyncpg://nativly:nativly@localhost:5432/nativly"


def normalize_database_url(url: str) -> str:
    """Accept provider URLs as copied (e.g. Neon's `postgresql://…?sslmode=require`).

    asyncpg needs the `postgresql+asyncpg` driver and takes `ssl=` instead of libpq's
    `sslmode=`; libpq-only options like `channel_binding` make it fail to connect.
    """
    parsed = make_url(url)
    if parsed.drivername in ("postgres", "postgresql"):
        parsed = parsed.set(drivername="postgresql+asyncpg")
    if parsed.drivername != "postgresql+asyncpg":
        return url
    query = dict(parsed.query)
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    if sslmode is not None and "ssl" not in query:
        query["ssl"] = sslmode
    return parsed.set(query=query).render_as_string(hide_password=False)


class Settings(BaseSettings):
    # hide_input_in_errors: validation errors must never echo raw env values (secrets, DB URLs).
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="NATIVLY_", extra="ignore", hide_input_in_errors=True
    )

    app_name: str = "Nativly API"
    environment: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = False

    database_url: str = _LOCAL_DATABASE_URL
    database_echo: bool = False

    # HS256 keys shorter than the 256-bit hash output weaken the signature (RFC 7518 §3.2).
    jwt_secret_key: SecretStr = Field(default=SecretStr(_INSECURE_DEV_SECRET), min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    cors_origins: list[str] = []

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        return normalize_database_url(value)

    @model_validator(mode="after")
    def _require_real_config_when_deployed(self) -> Self:
        if self.environment not in ("staging", "production"):
            return self
        if self.jwt_secret_key.get_secret_value() == _INSECURE_DEV_SECRET:
            raise ValueError("NATIVLY_JWT_SECRET_KEY must be set outside local/test environments")
        if self.database_url == _LOCAL_DATABASE_URL:
            raise ValueError("NATIVLY_DATABASE_URL must be set outside local/test environments")
        return self


@lru_cache
def get_settings() -> Settings:
    # Cached so the environment is read once per process; call get_settings.cache_clear() to reload.
    return Settings()
