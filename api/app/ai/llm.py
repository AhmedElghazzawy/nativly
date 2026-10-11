"""The single entry point for language-model calls: `LLM.complete()`.

Every call is quota-checked per learner, retried once on transient failures, validated
against a Pydantic schema, and recorded in `llm_calls` whatever the outcome.
"""

import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import Request
from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.models import LLMCall
from app.ai.providers import LLMProvider, Message, ProviderError, RawCompletion
from app.core.config import Settings

Tier = Literal["fast", "smart"]


class AIUnavailableError(Exception):
    """AI isn't configured, or the provider is down. Features should degrade, not crash."""


class AIQuotaExceededError(Exception):
    """The learner used today's AI allowance."""


@dataclass(frozen=True)
class Completion[T: BaseModel]:
    data: T
    call_id: uuid.UUID
    model: str


class LLM:
    def __init__(
        self,
        provider: LLMProvider | None,
        settings: Settings,
        sessionmaker: async_sessionmaker[AsyncSession],
    ) -> None:
        self.provider = provider
        self.settings = settings
        # Calls are logged in their own session/transaction, so a failed feature request
        # (rolled back) still leaves a record of what the model was asked and what it cost.
        self._sessionmaker = sessionmaker

    @property
    def enabled(self) -> bool:
        return self.provider is not None

    async def complete[T: BaseModel](
        self,
        *,
        purpose: str,
        prompt_version: str,
        user_id: uuid.UUID | None,
        system: str,
        messages: Sequence[Message],
        schema: type[T],
        tier: Tier = "fast",
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> Completion[T]:
        if self.provider is None:
            raise AIUnavailableError("AI features are not configured")
        if user_id is not None:
            await self._check_quota(user_id)

        model = self.settings.ai_model_smart if tier == "smart" else self.settings.ai_model_fast
        started = time.perf_counter()
        status, error, raw = "ok", None, None
        try:
            raw = await self._generate_with_retry(
                model, system, messages, schema, temperature, max_output_tokens
            )
            data = schema.model_validate_json(raw.text)
        except ProviderError as exc:
            status, error = "provider_error", str(exc)
            raise AIUnavailableError("The AI service is unavailable right now") from exc
        except ValidationError as exc:
            status, error = "invalid_output", str(exc)[:2000]
            raise AIUnavailableError("The AI returned an unusable answer") from exc
        finally:
            call_id = await self._record(
                purpose=purpose,
                prompt_version=prompt_version,
                user_id=user_id,
                model=model,
                status=status,
                error=error,
                raw=raw,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
        return Completion(data=data, call_id=call_id, model=model)

    async def _generate_with_retry(
        self,
        model: str,
        system: str,
        messages: Sequence[Message],
        schema: type[BaseModel],
        temperature: float,
        max_output_tokens: int,
    ) -> RawCompletion:
        assert self.provider is not None  # noqa: S101 - checked by the caller
        for attempt in (1, 2):
            try:
                return await self.provider.generate(
                    model=model,
                    system=system,
                    messages=messages,
                    schema=schema,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    timeout_seconds=self.settings.ai_timeout_seconds,
                )
            except ProviderError as exc:
                if attempt == 2 or not exc.retryable:
                    raise
        raise AssertionError("unreachable")  # pragma: no cover

    async def _check_quota(self, user_id: uuid.UUID) -> None:
        since = datetime.now(UTC) - timedelta(days=1)
        async with self._sessionmaker() as session:
            used = await session.scalar(
                select(func.count())
                .select_from(LLMCall)
                .where(LLMCall.user_id == user_id, LLMCall.created_at >= since)
            )
        if (used or 0) >= self.settings.ai_daily_calls_per_user:
            raise AIQuotaExceededError

    async def _record(
        self,
        *,
        purpose: str,
        prompt_version: str,
        user_id: uuid.UUID | None,
        model: str,
        status: str,
        error: str | None,
        raw: RawCompletion | None,
        latency_ms: int,
    ) -> uuid.UUID:
        assert self.provider is not None  # noqa: S101
        call = LLMCall(
            user_id=user_id,
            purpose=purpose,
            prompt_version=prompt_version,
            provider=self.provider.name,
            model=model,
            status=status,
            input_tokens=raw.input_tokens if raw else None,
            output_tokens=raw.output_tokens if raw else None,
            latency_ms=latency_ms,
            error=error,
        )
        async with self._sessionmaker() as session:
            session.add(call)
            await session.commit()
        return call.id


def create_provider(settings: Settings) -> LLMProvider | None:
    match settings.ai_provider:
        case "gemini":
            if settings.gemini_api_key is None:
                return None
            from app.ai.providers import GeminiProvider

            return GeminiProvider(settings.gemini_api_key.get_secret_value())
        case "fake":
            from app.ai.fake import demo_provider

            return demo_provider()
        case "disabled":
            return None


def get_llm(request: Request) -> LLM:
    llm: LLM = request.app.state.llm
    return llm
