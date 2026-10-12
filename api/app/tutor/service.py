"""Tutor conversations: assemble the learner's context, take a turn, remember what matters."""

import re
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLM
from app.learning.models import CefrLevel, Course
from app.learning.service import NotFoundError
from app.placement import staircase
from app.placement.models import SkillLevel
from app.tutor.models import LearnerFact, Speaker, TutorMessage, TutorSession
from app.tutor.prompt import (
    MAX_FACTS,
    PROMPT_VERSION,
    LearnerContext,
    TutorTurn,
    build_messages,
    greeting,
)
from app.writing.models import Mistake
from app.writing.service import record_mistakes

DEFAULT_LEVEL = CefrLevel.A2  # until the learner takes the placement test


def fact_key(fact: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", fact.lower()).strip()[:300]


async def learner_context(session: AsyncSession, user_id: uuid.UUID) -> LearnerContext:
    levels = (await session.scalars(select(SkillLevel).where(SkillLevel.user_id == user_id))).all()
    level = staircase.overall([s.cefr_level for s in levels]) if levels else DEFAULT_LEVEL
    course = await session.scalar(select(Course).where(Course.cefr_level == level).limit(1))
    facts = (
        await session.scalars(
            select(LearnerFact.fact)
            .where(LearnerFact.user_id == user_id)
            .order_by(LearnerFact.last_mentioned_at.desc())
            .limit(MAX_FACTS)
        )
    ).all()
    mistakes = (
        await session.execute(
            select(Mistake.original, Mistake.correction)
            .where(Mistake.user_id == user_id)
            .order_by(Mistake.count.desc(), Mistake.last_seen_at.desc())
            .limit(3)
        )
    ).all()
    return LearnerContext(
        level=level.value,
        skill_levels={s.skill.value: s.cefr_level.value for s in levels},
        course_title=course.title if course else None,
        facts=list(facts),
        recurring_mistakes=[(m.original, m.correction) for m in mistakes],
    )


async def start(session: AsyncSession, user_id: uuid.UUID) -> TutorSession:
    previous = await session.scalar(
        select(func.count()).select_from(TutorSession).where(TutorSession.user_id == user_id)
    )
    ctx = await learner_context(session, user_id)
    now = datetime.now(UTC)
    conversation = TutorSession(user_id=user_id, message_count=1, last_message_at=now)
    session.add(conversation)
    await session.flush()
    session.add(
        TutorMessage(
            session_id=conversation.id,
            speaker=Speaker.TUTOR,
            text=greeting(ctx, first_conversation=not previous),
            corrections=[],
            created_at=now,
        )
    )
    await session.commit()
    return conversation


async def get_owned(
    session: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID
) -> TutorSession:
    conversation = await session.scalar(
        select(TutorSession).where(TutorSession.id == session_id, TutorSession.user_id == user_id)
    )
    if conversation is None:
        raise NotFoundError
    return conversation


async def messages(session: AsyncSession, session_id: uuid.UUID) -> Sequence[TutorMessage]:
    result = await session.scalars(
        select(TutorMessage)
        .where(TutorMessage.session_id == session_id)
        .order_by(TutorMessage.created_at, TutorMessage.id)
    )
    return result.all()


async def send(
    session: AsyncSession, llm: LLM, user_id: uuid.UUID, session_id: uuid.UUID, text: str
) -> tuple[TutorMessage, TutorMessage]:
    """Store the learner's message, take the teacher's turn, and remember what matters.

    The learner's message is committed before the model call, so nothing they typed is lost if
    the AI is unavailable (the caller gets the error and can retry).
    """
    conversation = await get_owned(session, user_id, session_id)
    now = datetime.now(UTC)
    learner_message = TutorMessage(
        session_id=conversation.id,
        speaker=Speaker.LEARNER,
        text=text,
        corrections=[],
        created_at=now,
    )
    session.add(learner_message)
    conversation.message_count += 1
    conversation.last_message_at = now
    if conversation.title is None:
        conversation.title = text[:80]
    await session.commit()

    ctx = await learner_context(session, user_id)
    history = [(m.speaker.value, m.text) for m in await messages(session, conversation.id)]
    system, prompt = build_messages(ctx, history)
    completion = await llm.complete(
        purpose="tutor_chat",
        prompt_version=PROMPT_VERSION,
        user_id=user_id,
        system=system,
        messages=prompt,
        schema=TutorTurn,
        tier="smart",
        temperature=0.7,
    )
    turn = completion.data

    learner_message.corrections = [c.model_dump() for c in turn.corrections]
    reply = TutorMessage(
        session_id=conversation.id,
        speaker=Speaker.TUTOR,
        text=turn.reply,
        corrections=[],
        llm_call_id=completion.call_id,
        created_at=datetime.now(UTC),
    )
    session.add(reply)
    conversation.message_count += 1
    conversation.last_message_at = reply.created_at
    await record_mistakes(session, user_id, turn.corrections, source="tutor")
    await _remember(session, user_id, conversation.id, turn.new_facts)
    await session.commit()
    return learner_message, reply


async def _remember(
    session: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID, facts: Sequence[str]
) -> None:
    now = datetime.now(UTC)
    for fact in facts:
        key = fact_key(fact)
        if not key:
            continue
        stmt = insert(LearnerFact).values(
            id=uuid.uuid4(),
            user_id=user_id,
            key=key,
            fact=fact.strip()[:300],
            source_session_id=session_id,
            last_mentioned_at=now,
        )
        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=[LearnerFact.user_id, LearnerFact.key],
                set_={"last_mentioned_at": now},
            )
        )


async def list_sessions(session: AsyncSession, user_id: uuid.UUID) -> Sequence[TutorSession]:
    result = await session.scalars(
        select(TutorSession)
        .where(TutorSession.user_id == user_id)
        .order_by(TutorSession.last_message_at.desc().nulls_last())
        .limit(50)
    )
    return result.all()


async def list_facts(session: AsyncSession, user_id: uuid.UUID) -> Sequence[LearnerFact]:
    result = await session.scalars(
        select(LearnerFact)
        .where(LearnerFact.user_id == user_id)
        .order_by(LearnerFact.created_at.desc())
    )
    return result.all()


async def forget_fact(session: AsyncSession, user_id: uuid.UUID, fact_id: uuid.UUID) -> None:
    result = await session.execute(
        delete(LearnerFact).where(LearnerFact.id == fact_id, LearnerFact.user_id == user_id)
    )
    if result.rowcount == 0:  # type: ignore[attr-defined]
        raise NotFoundError
    await session.commit()


async def forget_everything(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(delete(LearnerFact).where(LearnerFact.user_id == user_id))
    await session.commit()
