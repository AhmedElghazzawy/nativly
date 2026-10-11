import pytest
from pydantic import ValidationError

from app.core.config import Settings, normalize_database_url

STRONG_SECRET = "s" * 64
REMOTE_DB = "postgresql+asyncpg://u:p@db.example.com:5432/app"


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_deployed_environments_require_a_real_jwt_secret(environment: str) -> None:
    with pytest.raises(ValidationError, match="NATIVLY_JWT_SECRET_KEY"):
        Settings(environment=environment, database_url=REMOTE_DB)


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_deployed_environments_require_a_real_database_url(environment: str) -> None:
    with pytest.raises(ValidationError, match="NATIVLY_DATABASE_URL"):
        Settings(environment=environment, jwt_secret_key=STRONG_SECRET)


def test_short_jwt_secret_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret_key="too-short")


def test_production_accepts_complete_config() -> None:
    settings = Settings(
        environment="production", jwt_secret_key=STRONG_SECRET, database_url=REMOTE_DB
    )

    assert settings.environment == "production"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Neon's copy-paste format: libpq options translated for asyncpg.
        (
            "postgresql://owner:pw@ep-x.eu-central-1.aws.neon.tech/neondb"
            "?sslmode=require&channel_binding=require",
            "postgresql+asyncpg://owner:pw@ep-x.eu-central-1.aws.neon.tech/neondb?ssl=require",
        ),
        # Heroku-style scheme.
        ("postgres://u:p@h:5432/d", "postgresql+asyncpg://u:p@h:5432/d"),
        # Already correct: unchanged.
        (REMOTE_DB, REMOTE_DB),
        ("postgresql+asyncpg://u:p@h/d?ssl=require", "postgresql+asyncpg://u:p@h/d?ssl=require"),
    ],
)
def test_normalize_database_url(raw: str, expected: str) -> None:
    assert normalize_database_url(raw) == expected


def test_settings_normalizes_database_url() -> None:
    settings = Settings(database_url="postgresql://u:p@h/d?sslmode=require")

    assert settings.database_url == "postgresql+asyncpg://u:p@h/d?ssl=require"
