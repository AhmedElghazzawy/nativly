import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshToken, User
from app.auth.schemas import TokenPair
from app.core.config import Settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def register_user(session: AsyncSession, email: str, password: str) -> User:
    user = User(email=normalize_email(email), password_hash=hash_password(password))
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        # Rely on the unique constraint rather than a pre-check, which would race.
        await session.rollback()
        raise EmailAlreadyRegisteredError from exc
    await session.refresh(user)
    return user


async def authenticate(session: AsyncSession, email: str, password: str) -> User:
    user = await session.scalar(select(User).where(User.email == normalize_email(email)))
    if not verify_password(password, user.password_hash if user else None):
        raise InvalidCredentialsError
    assert user is not None  # noqa: S101 - narrowed by verify_password returning True
    if not user.is_active:
        raise InvalidCredentialsError
    return user


async def issue_tokens(session: AsyncSession, user: User, settings: Settings) -> TokenPair:
    raw_refresh = generate_refresh_token()
    now = datetime.now(UTC)
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            created_at=now,
            expires_at=now + timedelta(days=settings.refresh_token_ttl_days),
        )
    )
    await session.commit()
    return TokenPair(
        access_token=create_access_token(user.id, settings),
        refresh_token=raw_refresh,
        expires_in=settings.access_token_ttl_minutes * 60,
    )


async def rotate_refresh_token(
    session: AsyncSession, raw_token: str, settings: Settings
) -> TokenPair:
    stored = await session.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(raw_token))
        .with_for_update()
    )
    now = datetime.now(UTC)
    if stored is None:
        raise InvalidRefreshTokenError

    if stored.revoked_at is not None:
        # A revoked token being replayed means it was likely stolen: log the user out everywhere.
        await _revoke_all_for_user(session, stored.user_id, now)
        await session.commit()
        raise InvalidRefreshTokenError

    user = await session.get(User, stored.user_id)
    if stored.expires_at <= now or user is None or not user.is_active:
        raise InvalidRefreshTokenError

    stored.revoked_at = now
    return await issue_tokens(session, user, settings)


async def revoke_refresh_token(session: AsyncSession, raw_token: str) -> None:
    await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == hash_refresh_token(raw_token),
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    await session.commit()


async def get_active_user(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    user = await session.get(User, user_id)
    return user if user is not None and user.is_active else None


async def _revoke_all_for_user(session: AsyncSession, user_id: uuid.UUID, now: datetime) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
