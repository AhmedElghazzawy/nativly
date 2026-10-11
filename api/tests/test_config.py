import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_deployed_environments_require_a_real_jwt_secret(environment: str) -> None:
    with pytest.raises(ValidationError, match="NATIVLY_JWT_SECRET_KEY"):
        Settings(environment=environment)


def test_short_jwt_secret_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret_key="too-short")


def test_production_accepts_strong_secret() -> None:
    settings = Settings(environment="production", jwt_secret_key="s" * 64)

    assert settings.environment == "production"
