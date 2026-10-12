from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.ai.llm import LLM, create_provider
from app.auth.router import router as auth_router
from app.core.config import Settings, get_settings
from app.core.db import create_engine, create_sessionmaker
from app.learning.router import router as learning_router
from app.placement.router import router as placement_router
from app.vocab.router import router as vocab_router
from app.writing.router import router as writing_router

API_PREFIX = "/api/v1"


class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings)
        app.state.engine = engine
        app.state.sessionmaker = create_sessionmaker(engine)
        app.state.llm = LLM(create_provider(settings), settings, app.state.sessionmaker)
        yield
        await engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/health", tags=["meta"], summary="Liveness: the process is up")
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get(
        "/health/ready",
        tags=["meta"],
        summary="Readiness: dependencies are reachable",
        responses={503: {"model": HealthResponse}},
    )
    async def ready(request: Request) -> JSONResponse:
        try:
            async with request.app.state.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except (SQLAlchemyError, OSError):
            return JSONResponse(status_code=503, content={"status": "unavailable"})
        return JSONResponse(content={"status": "ok"})

    # HEAD too: uptime monitors and wait-for scripts probe with HEAD. Registered separately and
    # kept out of the schema, so OpenAPI operation IDs stay deterministic (GET only).
    app.head("/health", include_in_schema=False)(health)
    app.head("/health/ready", include_in_schema=False)(ready)

    app.include_router(auth_router, prefix=API_PREFIX)
    app.include_router(learning_router, prefix=API_PREFIX)
    app.include_router(vocab_router, prefix=API_PREFIX)
    app.include_router(writing_router, prefix=API_PREFIX)
    app.include_router(placement_router, prefix=API_PREFIX)

    return app


app = create_app()
