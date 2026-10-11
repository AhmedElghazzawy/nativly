import os
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.ai.llm import LLM
from app.ai.providers import FakeProvider
from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.main import create_app
from app.models import Base
from tests.content import ContentDir

TEST_DATABASE_URL = os.environ.get(
    "NATIVLY_TEST_DATABASE_URL",
    "postgresql+asyncpg://nativly:nativly@localhost:5432/nativly_test",
)


async def _ensure_database_exists(url: str) -> None:
    parsed = make_url(url)
    conn = await asyncpg.connect(
        user=parsed.username,
        password=parsed.password,
        host=parsed.host,
        port=parsed.port,
        database="postgres",
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", parsed.database
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{parsed.database}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(environment="test", database_url=TEST_DATABASE_URL)


@pytest.fixture(scope="session")
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    await _ensure_database_exists(settings.database_url)
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def connection(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    # Every test runs inside one outer transaction that is rolled back afterwards, so
    # commits made by app code become savepoints and nothing leaks between tests.
    async with engine.connect() as conn:
        transaction = await conn.begin()
        yield conn
        await transaction.rollback()


@pytest.fixture
async def session(connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    ) as session:
        yield session


@pytest.fixture
def fake_ai() -> FakeProvider:
    """The model provider used by the app in tests. Set `.responder` or `.fail_with`."""
    return FakeProvider()


@pytest.fixture
def llm(settings: Settings, connection: AsyncConnection, fake_ai: FakeProvider) -> LLM:
    # LLM logs calls in its own sessions; bind them to the test connection so they join
    # (and are rolled back with) the test's transaction.
    sessions = async_sessionmaker(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    return LLM(fake_ai, settings, sessions)


@pytest.fixture
def app(settings: Settings, engine: AsyncEngine, session: AsyncSession, llm: LLM) -> FastAPI:
    app = create_app(settings)
    # httpx's ASGITransport doesn't run the lifespan, so wire state the way it would.
    app.state.engine = engine
    app.state.llm = llm
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_session] = lambda: session
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    credentials = {"email": "learner@example.com", "password": "learner-password"}
    await client.post("/api/v1/auth/register", json=credentials)
    response = await client.post("/api/v1/auth/login", json=credentials)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def content(tmp_path: Path) -> ContentDir:
    return ContentDir(tmp_path / "content")
