from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEV_SECRET = "insecure-local-dev-only-secret-0000"  # noqa: S105 - local-only fallback


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="NATIVLY_", extra="ignore")

    app_name: str = "Nativly API"
    environment: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://nativly:nativly@localhost:5432/nativly"
    database_echo: bool = False

    # HS256 keys shorter than the 256-bit hash output weaken the signature (RFC 7518 §3.2).
    jwt_secret_key: SecretStr = Field(default=SecretStr(_INSECURE_DEV_SECRET), min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    cors_origins: list[str] = []

    @model_validator(mode="after")
    def _require_real_secret_outside_local(self) -> Self:
        if (
            self.environment in ("staging", "production")
            and self.jwt_secret_key.get_secret_value() == _INSECURE_DEV_SECRET
        ):
            raise ValueError("NATIVLY_JWT_SECRET_KEY must be set outside local/test environments")
        return self


@lru_cache
def get_settings() -> Settings:
    # Cached so the environment is read once per process; call get_settings.cache_clear() to reload.
    return Settings()
