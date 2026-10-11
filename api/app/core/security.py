import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import Settings

_password_hash = PasswordHash.recommended()  # Argon2id with library-maintained parameters

# Verified against when the user doesn't exist, so login takes the same time either way
# and response timing can't be used to discover which emails are registered.
_DUMMY_HASH = _password_hash.hash(secrets.token_urlsafe(16))

ACCESS_TOKEN_TYPE = "access"  # noqa: S105 - token type label, not a secret


class InvalidTokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _password_hash.verify(password, _DUMMY_HASH)
        return False
    return _password_hash.verify(password, password_hash)


def create_access_token(user_id: uuid.UUID, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(
        payload, settings.jwt_secret_key.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str, settings: Settings) -> uuid.UUID:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "iat", "type"]},
        )
        if payload["type"] != ACCESS_TOKEN_TYPE:
            raise InvalidTokenError("wrong token type")
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError) as exc:
        raise InvalidTokenError(str(exc)) from exc


def generate_refresh_token() -> str:
    # Opaque, not a JWT: refresh tokens are always checked against the database anyway,
    # so a random string is simpler and leaks nothing if logged.
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    # A fast hash is fine here: the input is 384 bits of randomness, not a guessable password.
    return hashlib.sha256(token.encode()).hexdigest()
