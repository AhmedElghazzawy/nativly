import json
import uuid
from collections.abc import Sequence

import pytest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.fake import demo_provider
from app.ai.llm import LLM, AIQuotaExceededError, AIUnavailableError
from app.ai.models import LLMCall
from app.ai.providers import FakeProvider, Message, ProviderError
from app.auth.models import User
from app.core.config import Settings
from app.writing.feedback import WritingFeedback, build_messages


class Answer(BaseModel):
    value: int


async def call(llm: LLM, user_id: uuid.UUID | None = None) -> Answer:
    completion = await llm.complete(
        purpose="test",
        prompt_version="test-v1",
        user_id=user_id,
        system="system",
        messages=[Message(role="user", text="question")],
        schema=Answer,
    )
    return completion.data


async def calls(session: AsyncSession) -> list[LLMCall]:
    return list((await session.scalars(select(LLMCall).order_by(LLMCall.created_at))).all())


@pytest.fixture
async def user(session: AsyncSession) -> User:
    user = User(email="ai@example.com", password_hash="x")
    session.add(user)
    await session.flush()
    return user


async def test_successful_call_is_parsed_and_recorded(
    llm: LLM, fake_ai: FakeProvider, session: AsyncSession, user: User
) -> None:
    fake_ai.responder = lambda system, messages: '{"value": 42}'

    answer = await call(llm, user.id)

    assert answer == Answer(value=42)
    [record] = await calls(session)
    assert (record.status, record.purpose, record.prompt_version) == ("ok", "test", "test-v1")
    assert record.user_id == user.id
    assert record.provider == "fake"
    assert record.output_tokens is not None


async def test_invalid_model_output_is_rejected_and_recorded(
    llm: LLM, fake_ai: FakeProvider, session: AsyncSession
) -> None:
    fake_ai.responder = lambda system, messages: '{"value": "not a number"}'

    with pytest.raises(AIUnavailableError):
        await call(llm)

    [record] = await calls(session)
    assert record.status == "invalid_output"
    assert record.error


async def test_transient_provider_errors_are_retried_once(llm: LLM, fake_ai: FakeProvider) -> None:
    attempts = 0

    def flaky(system: str, messages: Sequence[Message]) -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ProviderError("503", retryable=True)
        return '{"value": 1}'

    fake_ai.responder = flaky

    assert (await call(llm)).value == 1
    assert attempts == 2


async def test_permanent_provider_errors_fail_fast_and_are_recorded(
    llm: LLM, fake_ai: FakeProvider, session: AsyncSession
) -> None:
    fake_ai.fail_with = ProviderError("400 bad request", retryable=False)

    with pytest.raises(AIUnavailableError):
        await call(llm)

    assert len(fake_ai.calls) == 1
    [record] = await calls(session)
    assert record.status == "provider_error"
    assert "400" in (record.error or "")


async def test_daily_quota_per_learner(
    llm: LLM, fake_ai: FakeProvider, settings: Settings, user: User
) -> None:
    llm.settings = settings.model_copy(update={"ai_daily_calls_per_user": 2})
    fake_ai.responder = lambda system, messages: '{"value": 1}'
    await call(llm, user.id)
    await call(llm, user.id)

    with pytest.raises(AIQuotaExceededError):
        await call(llm, user.id)
    assert len(fake_ai.calls) == 2  # the provider was never asked the third time


async def test_unconfigured_ai_is_unavailable(llm: LLM) -> None:
    llm.provider = None

    with pytest.raises(AIUnavailableError, match="not configured"):
        await call(llm)


async def test_demo_provider_returns_valid_writing_feedback() -> None:
    system, messages = build_messages(
        level="A2", task_prompt="Write about your weekend.", guidance=[], text="I go to park."
    )

    raw = await demo_provider().generate(
        model="demo",
        system=system,
        messages=messages,
        schema=WritingFeedback,
        temperature=0,
        max_output_tokens=100,
        timeout_seconds=1,
    )

    feedback = WritingFeedback.model_validate(json.loads(raw.text))
    assert feedback.corrected_text == "I go to park."
    assert "Demo mode" in feedback.strengths[0]
