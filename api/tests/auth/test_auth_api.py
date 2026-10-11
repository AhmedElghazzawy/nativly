from typing import Any

import pytest
from httpx import AsyncClient
from pydantic import SecretStr
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.config import Settings
from app.core.security import create_access_token

API = "/api/v1/auth"
EMAIL = "ada@example.com"
PASSWORD = "correct horse battery"


async def register(client: AsyncClient, email: str = EMAIL, password: str = PASSWORD) -> Any:
    response = await client.post(f"{API}/register", json={"email": email, "password": password})
    assert response.status_code == 201, response.text
    return response.json()


async def login(client: AsyncClient, email: str = EMAIL, password: str = PASSWORD) -> Any:
    response = await client.post(f"{API}/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- register -------------------------------------------------------------------------------


async def test_register_creates_user_without_exposing_password(client: AsyncClient) -> None:
    body = await register(client)

    assert body["email"] == EMAIL
    assert body["is_active"] is True
    assert "password" not in body
    assert "password_hash" not in body


async def test_register_normalizes_email_and_rejects_duplicates(client: AsyncClient) -> None:
    await register(client, email="Ada@Example.com")

    response = await client.post(
        f"{API}/register", json={"email": "ada@example.com", "password": PASSWORD}
    )

    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": PASSWORD},
        {"email": EMAIL, "password": "short"},
        {"email": EMAIL, "password": "x" * 129},
        {"email": EMAIL},
    ],
)
async def test_register_rejects_invalid_input(client: AsyncClient, payload: dict[str, str]) -> None:
    response = await client.post(f"{API}/register", json=payload)

    assert response.status_code == 422


# --- login ----------------------------------------------------------------------------------


async def test_login_returns_token_pair(client: AsyncClient, settings: Settings) -> None:
    await register(client)

    body = await login(client, email="ADA@example.com")

    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.access_token_ttl_minutes * 60
    assert body["access_token"]
    assert body["refresh_token"]


@pytest.mark.parametrize(
    ("email", "password"),
    [(EMAIL, "wrong password!"), ("nobody@example.com", PASSWORD)],
)
async def test_login_rejects_bad_credentials_with_same_error(
    client: AsyncClient, email: str, password: str
) -> None:
    await register(client)

    response = await client.post(f"{API}/login", json={"email": email, "password": password})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


async def test_login_rejects_inactive_user(client: AsyncClient, session: AsyncSession) -> None:
    await register(client)
    await session.execute(update(User).where(User.email == EMAIL).values(is_active=False))

    response = await client.post(f"{API}/login", json={"email": EMAIL, "password": PASSWORD})

    assert response.status_code == 401


# --- /me ------------------------------------------------------------------------------------


async def test_me_returns_current_user(client: AsyncClient) -> None:
    user = await register(client)
    tokens = await login(client)

    response = await client.get(f"{API}/me", headers=bearer(tokens["access_token"]))

    assert response.status_code == 200
    assert response.json()["id"] == user["id"]


@pytest.mark.parametrize("headers", [{}, bearer("not-a-jwt"), {"Authorization": "Basic abc"}])
async def test_me_rejects_missing_or_malformed_token(
    client: AsyncClient, headers: dict[str, str]
) -> None:
    response = await client.get(f"{API}/me", headers=headers)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_me_rejects_expired_token(client: AsyncClient, settings: Settings) -> None:
    user = await register(client)
    expired_settings = settings.model_copy(update={"access_token_ttl_minutes": -1})
    token = create_access_token(user["id"], expired_settings)

    response = await client.get(f"{API}/me", headers=bearer(token))

    assert response.status_code == 401


async def test_me_rejects_token_signed_with_another_key(
    client: AsyncClient, settings: Settings
) -> None:
    user = await register(client)
    forged_settings = settings.model_copy(
        update={"jwt_secret_key": SecretStr("attacker-controlled-key-of-sufficient-length")}
    )
    token = create_access_token(user["id"], forged_settings)

    response = await client.get(f"{API}/me", headers=bearer(token))

    assert response.status_code == 401


# --- refresh / logout -----------------------------------------------------------------------


async def test_refresh_rotates_tokens(client: AsyncClient) -> None:
    await register(client)
    first = await login(client)

    response = await client.post(f"{API}/refresh", json={"refresh_token": first["refresh_token"]})

    assert response.status_code == 200
    second = response.json()
    assert second["refresh_token"] != first["refresh_token"]
    me = await client.get(f"{API}/me", headers=bearer(second["access_token"]))
    assert me.status_code == 200


async def test_refresh_token_cannot_be_used_twice(client: AsyncClient) -> None:
    await register(client)
    first = await login(client)
    await client.post(f"{API}/refresh", json={"refresh_token": first["refresh_token"]})

    replay = await client.post(f"{API}/refresh", json={"refresh_token": first["refresh_token"]})

    assert replay.status_code == 401


async def test_refresh_token_reuse_revokes_all_sessions(client: AsyncClient) -> None:
    await register(client)
    first = await login(client)
    rotated = (
        await client.post(f"{API}/refresh", json={"refresh_token": first["refresh_token"]})
    ).json()

    # An attacker replays the stolen, already-rotated token...
    await client.post(f"{API}/refresh", json={"refresh_token": first["refresh_token"]})

    # ...so the legitimate user's newer token is revoked too.
    response = await client.post(f"{API}/refresh", json={"refresh_token": rotated["refresh_token"]})
    assert response.status_code == 401


async def test_refresh_rejects_unknown_token(client: AsyncClient) -> None:
    response = await client.post(f"{API}/refresh", json={"refresh_token": "made-up"})

    assert response.status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    await register(client)
    tokens = await login(client)

    logout = await client.post(f"{API}/logout", json={"refresh_token": tokens["refresh_token"]})
    response = await client.post(f"{API}/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert logout.status_code == 204
    assert response.status_code == 401
