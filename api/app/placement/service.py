"""Running a placement test: the server picks every question and grades every answer."""

import random
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning.models import CefrLevel, Course, Skill
from app.learning.service import NotFoundError
from app.placement import staircase
from app.placement.models import (
    PlacementItem,
    PlacementResponse,
    PlacementSession,
    SessionStatus,
    SkillLevel,
)


class WrongItemError(Exception):
    """The answer isn't for the question the server is waiting for (stale tab, replay)."""


class SessionClosedError(Exception):
    pass


def _initial_state() -> dict[str, Any]:
    return {skill.value: {"level": staircase.START_LEVEL, "asked": 0} for skill in staircase.SKILLS}


def _current_skill(state: dict[str, Any]) -> Skill | None:
    for skill in staircase.SKILLS:
        if state[skill.value]["asked"] < staircase.QUESTIONS_PER_SKILL:
            return skill
    return None


def progress(session: PlacementSession) -> tuple[int, int]:
    """(questions answered, total questions)."""
    answered = sum(s["asked"] for s in session.state.values())
    return answered, staircase.QUESTIONS_PER_SKILL * len(staircase.SKILLS)


async def current_session(session: AsyncSession, user_id: uuid.UUID) -> PlacementSession | None:
    return await session.scalar(
        select(PlacementSession)
        .where(PlacementSession.user_id == user_id)
        .order_by(PlacementSession.started_at.desc())
        .limit(1)
    )


async def start(session: AsyncSession, user_id: uuid.UUID, language: str) -> PlacementSession:
    """Resume the learner's unfinished test, or start a new one."""
    latest = await current_session(session, user_id)
    if latest is not None and latest.status == SessionStatus.IN_PROGRESS:
        return latest
    test = PlacementSession(
        user_id=user_id,
        language=language,
        status=SessionStatus.IN_PROGRESS,
        state=_initial_state(),
    )
    session.add(test)
    await session.flush()
    await _queue_next_item(session, test)
    await session.commit()
    return test


async def pending_item(session: AsyncSession, test: PlacementSession) -> PlacementItem | None:
    if test.pending_item_id is None:
        return None
    return await session.get(PlacementItem, test.pending_item_id)


async def _queue_next_item(session: AsyncSession, test: PlacementSession) -> None:
    """Pick an unseen item at the skill's current level (nearest level if exhausted)."""
    while (skill := _current_skill(test.state)) is not None:
        seen = select(PlacementResponse.item_id).where(PlacementResponse.session_id == test.id)
        target = test.state[skill.value]["level"]
        by_distance = sorted(range(len(staircase.LEVELS)), key=lambda i: (abs(i - target), -i))
        for index in by_distance:
            candidates = (
                await session.scalars(
                    select(PlacementItem.id).where(
                        PlacementItem.language == test.language,
                        PlacementItem.skill == skill,
                        PlacementItem.cefr_level == staircase.LEVELS[index],
                        PlacementItem.id.not_in(seen),
                    )
                )
            ).all()
            if candidates:
                # Random among equivalent items, so retakes and classmates see different ones.
                test.pending_item_id = random.choice(candidates)  # noqa: S311
                return
        # The bank has nothing left for this skill: end it with what we have.
        test.state = {**test.state, skill.value: {**test.state[skill.value], "asked": 99}}
    test.pending_item_id = None


async def answer(
    session: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    item_slug: str,
    choice: int,
    duration_ms: int | None,
) -> PlacementSession:
    test = await session.scalar(
        select(PlacementSession)
        .where(PlacementSession.id == session_id, PlacementSession.user_id == user_id)
        .with_for_update()
    )
    if test is None:
        raise NotFoundError
    if test.status != SessionStatus.IN_PROGRESS:
        raise SessionClosedError
    item = await pending_item(session, test)
    if item is None or item.slug != item_slug:
        raise WrongItemError
    if not 0 <= choice < len(item.options):
        raise ValueError("choice is out of range")

    correct = choice == item.answer
    session.add(
        PlacementResponse(
            session_id=test.id,
            item_id=item.id,
            skill=item.skill,
            cefr_level=item.cefr_level,
            choice=choice,
            is_correct=correct,
            duration_ms=duration_ms,
        )
    )
    skill_state = test.state[item.skill.value]
    test.state = {
        **test.state,
        item.skill.value: {
            "level": staircase.next_level(skill_state["level"], correct),
            "asked": skill_state["asked"] + 1,
        },
    }
    await session.flush()
    await _queue_next_item(session, test)
    if test.pending_item_id is None:
        await _complete(session, test)
    await session.commit()
    return test


async def _complete(session: AsyncSession, test: PlacementSession) -> None:
    responses = (
        await session.scalars(
            select(PlacementResponse).where(PlacementResponse.session_id == test.id)
        )
    ).all()
    estimates: dict[Skill, staircase.Estimate] = {}
    for skill in staircase.SKILLS:
        answers = [
            staircase.Answer(r.cefr_level, r.is_correct) for r in responses if r.skill == skill
        ]
        if answers:
            estimates[skill] = staircase.estimate(answers)

    overall = staircase.overall([e.level for e in estimates.values()]) if estimates else None
    now = datetime.now(UTC)
    for skill, est in estimates.items():
        stmt = insert(SkillLevel).values(
            user_id=test.user_id,
            skill=skill,
            cefr_level=est.level,
            score=est.score,
            source="placement",
            updated_at=now,
        )
        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=[SkillLevel.user_id, SkillLevel.skill],
                set_={
                    "cefr_level": est.level,
                    "score": est.score,
                    "source": "placement",
                    "updated_at": now,
                },
            )
        )

    test.status = SessionStatus.COMPLETED
    test.completed_at = now
    test.result = {
        "skills": {
            s.value: {"level": e.level.value, "score": e.score} for s, e in estimates.items()
        },
        "overall": overall.value if overall else None,
        "recommended_course": await _course_for(session, test.language, overall),
    }


async def _course_for(session: AsyncSession, language: str, level: CefrLevel | None) -> str | None:
    """The course at the learner's level, else the closest one below it, else the lowest."""
    courses = (await session.scalars(select(Course).where(Course.language == language))).all()
    if not courses:
        return None
    order = list(CefrLevel)
    ranked = sorted(courses, key=lambda c: order.index(c.cefr_level))
    if level is None:
        return ranked[0].slug
    at_or_below = [c for c in ranked if order.index(c.cefr_level) <= order.index(level)]
    return (at_or_below[-1] if at_or_below else ranked[0]).slug


async def skill_levels(session: AsyncSession, user_id: uuid.UUID) -> list[SkillLevel]:
    rows = await session.scalars(select(SkillLevel).where(SkillLevel.user_id == user_id))
    order = list(Skill)
    return sorted(rows.all(), key=lambda s: order.index(s.skill))
