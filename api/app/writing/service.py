"""Writing submissions: word-count checks, AI feedback, and recording recurring mistakes."""

import re
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.llm import LLM
from app.learning.service import NotFoundError
from app.writing.feedback import PROMPT_VERSION, WritingFeedback, build_messages
from app.writing.models import Mistake, MistakeCategory, WritingSubmission, WritingTask

# Words may contain apostrophes (straight or curly) and hyphens: don't, it\u2019s, well-known.
_WORD = re.compile("[A-Za-z0-9]+(?:['\u2019-][A-Za-z0-9]+)*")


class WordCountError(ValueError):
    pass


def count_words(text: str) -> int:
    return len(_WORD.findall(text))


def mistake_key(original: str, correction: str) -> str:
    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s.strip().lower())[:190]

    return f"{norm(original)} -> {norm(correction)}"


async def get_task(session: AsyncSession, slug: str) -> WritingTask:
    task = await session.scalar(
        select(WritingTask)
        .where(WritingTask.slug == slug)
        .options(selectinload(WritingTask.objective))
    )
    if task is None:
        raise NotFoundError
    return task


async def submit(
    session: AsyncSession, llm: LLM, user_id: uuid.UUID, task_slug: str, text: str
) -> tuple[WritingSubmission, WritingFeedback]:
    task = await get_task(session, task_slug)
    words = count_words(text)
    if words < task.min_words:
        raise WordCountError(f"Write at least {task.min_words} words (you have {words}).")
    if words > task.max_words:
        raise WordCountError(f"Keep it under {task.max_words} words (you have {words}).")

    system, messages = build_messages(
        level=task.cefr_level, task_prompt=task.prompt, guidance=task.guidance, text=text
    )
    completion = await llm.complete(
        purpose="writing_feedback",
        prompt_version=PROMPT_VERSION,
        user_id=user_id,
        system=system,
        messages=messages,
        schema=WritingFeedback,
        tier="fast",
    )
    feedback = completion.data
    submission = WritingSubmission(
        user_id=user_id,
        task_id=task.id,
        text=text,
        word_count=words,
        feedback=feedback.model_dump(),
        cefr_estimate=feedback.cefr_estimate,
        prompt_version=PROMPT_VERSION,
        llm_call_id=completion.call_id,
    )
    session.add(submission)
    await record_mistakes(session, user_id, feedback.errors, source="writing")
    await session.commit()
    await session.refresh(submission)
    return submission, feedback


class MistakeInput(Protocol):
    # Read-only properties, so models with narrower types (Literal categories) still match.
    @property
    def original(self) -> str: ...
    @property
    def correction(self) -> str: ...
    @property
    def category(self) -> str: ...
    @property
    def explanation(self) -> str: ...


async def record_mistakes(
    session: AsyncSession, user_id: uuid.UUID, errors: Sequence[MistakeInput], source: str
) -> None:
    """Upsert each error into the learner's mistake log (writing, tutor, later speaking)."""
    now = datetime.now(UTC)
    for error in errors:
        if not error.original.strip() or error.original.strip() == error.correction.strip():
            continue
        stmt = insert(Mistake).values(
            id=uuid.uuid4(),
            user_id=user_id,
            key=mistake_key(error.original, error.correction),
            category=MistakeCategory(error.category),
            original=error.original[:300],
            correction=error.correction[:300],
            explanation=error.explanation,
            source=source,
            count=1,
            first_seen_at=now,
            last_seen_at=now,
        )
        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=[Mistake.user_id, Mistake.key],
                set_={
                    "count": Mistake.count + 1,
                    "last_seen_at": now,
                    "explanation": stmt.excluded.explanation,
                },
            )
        )


async def list_submissions(
    session: AsyncSession, user_id: uuid.UUID, task_slug: str
) -> Sequence[WritingSubmission]:
    task = await get_task(session, task_slug)
    result = await session.scalars(
        select(WritingSubmission)
        .where(WritingSubmission.user_id == user_id, WritingSubmission.task_id == task.id)
        .order_by(WritingSubmission.created_at.desc())
    )
    return result.all()


async def top_mistakes(session: AsyncSession, user_id: uuid.UUID, limit: int) -> Sequence[Mistake]:
    result = await session.scalars(
        select(Mistake)
        .where(Mistake.user_id == user_id)
        .order_by(Mistake.count.desc(), Mistake.last_seen_at.desc())
        .limit(limit)
    )
    return result.all()
