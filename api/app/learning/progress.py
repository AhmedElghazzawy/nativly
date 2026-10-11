"""Attempts, objective mastery and lesson progress for a learner."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.learning.grading import MASTERY_RATE, Grade, ResponseMismatchError, grade
from app.learning.models import (
    Exercise,
    ExerciseAttempt,
    Lesson,
    LessonProgress,
    LessonStatus,
    LessonStep,
    ObjectiveMastery,
)
from app.learning.schemas import AttemptRequest
from app.learning.service import NotFoundError


class ExerciseNotInLessonError(Exception):
    pass


class LessonIncompleteError(Exception):
    def __init__(self, missing: int) -> None:
        super().__init__(f"{missing} exercise(s) not attempted yet")
        self.missing = missing


@dataclass(frozen=True)
class AttemptOutcome:
    grade: Grade
    explanation: str
    objective_slug: str
    mastery: float


async def submit_attempt(
    session: AsyncSession, user_id: uuid.UUID, exercise_slug: str, request: AttemptRequest
) -> AttemptOutcome:
    exercise = await session.scalar(
        select(Exercise)
        .where(Exercise.slug == exercise_slug)
        .options(selectinload(Exercise.objective))
    )
    if exercise is None:
        raise NotFoundError
    if request.response.type != exercise.type:
        raise ResponseMismatchError(f"this is a {exercise.type} exercise")

    lesson_id = None
    if request.lesson_slug is not None:
        lesson_id = await _lesson_containing(session, request.lesson_slug, exercise.id)

    result = grade(
        exercise.type,
        exercise.payload,
        exercise.answer,
        request.response.model_dump(exclude={"type"}),
    )
    now = datetime.now(UTC)
    session.add(
        ExerciseAttempt(
            user_id=user_id,
            exercise_id=exercise.id,
            lesson_id=lesson_id,
            response=request.response.model_dump(),
            score=result.score,
            is_correct=result.is_correct,
            duration_ms=request.duration_ms,
            created_at=now,
        )
    )
    mastery = await _record_mastery(session, user_id, exercise.objective_id, result.score, now)
    if lesson_id is not None:
        await session.execute(
            insert(LessonProgress)
            .values(
                user_id=user_id,
                lesson_id=lesson_id,
                status=LessonStatus.IN_PROGRESS,
                started_at=now,
            )
            .on_conflict_do_nothing()  # keeps "completed" when a learner retakes a lesson
        )
    await session.commit()
    return AttemptOutcome(result, exercise.answer["explanation"], exercise.objective.slug, mastery)


async def _lesson_containing(
    session: AsyncSession, lesson_slug: str, exercise_id: uuid.UUID
) -> uuid.UUID:
    lesson_id = await session.scalar(select(Lesson.id).where(Lesson.slug == lesson_slug))
    if lesson_id is None:
        raise NotFoundError
    in_lesson = await session.scalar(
        select(LessonStep.id).where(
            LessonStep.lesson_id == lesson_id, LessonStep.exercise_id == exercise_id
        )
    )
    if in_lesson is None:
        raise ExerciseNotInLessonError
    return lesson_id


async def _record_mastery(
    session: AsyncSession,
    user_id: uuid.UUID,
    objective_id: uuid.UUID,
    score: float,
    now: datetime,
) -> float:
    # One atomic statement, so concurrent attempts can't lose each other's update.
    # First attempt: 0 + r*(s - 0) = r*s. Later: m + r*(s - m) = (1 - r)*m + r*s,
    # and `excluded.mastery` already holds r*s.
    base = insert(ObjectiveMastery).values(
        user_id=user_id,
        objective_id=objective_id,
        mastery=MASTERY_RATE * score,
        evidence_count=1,
        last_seen_at=now,
    )
    upsert = base.on_conflict_do_update(
        index_elements=[ObjectiveMastery.user_id, ObjectiveMastery.objective_id],
        set_={
            "mastery": (1 - MASTERY_RATE) * ObjectiveMastery.mastery + base.excluded.mastery,
            "evidence_count": ObjectiveMastery.evidence_count + 1,
            "last_seen_at": base.excluded.last_seen_at,
        },
    ).returning(ObjectiveMastery.mastery)
    return float((await session.execute(upsert)).scalar_one())


async def complete_lesson(
    session: AsyncSession, user_id: uuid.UUID, lesson_slug: str
) -> tuple[LessonProgress, Lesson]:
    lesson = await session.scalar(
        select(Lesson).where(Lesson.slug == lesson_slug).options(selectinload(Lesson.steps))
    )
    if lesson is None:
        raise NotFoundError
    exercise_ids = {s.exercise_id for s in lesson.steps if s.exercise_id is not None}

    # Latest attempt per exercise in this lesson: the lesson score reflects where the
    # learner ended up, not their first try.
    latest = (
        select(ExerciseAttempt.exercise_id, ExerciseAttempt.score)
        .where(ExerciseAttempt.user_id == user_id, ExerciseAttempt.lesson_id == lesson.id)
        .order_by(ExerciseAttempt.exercise_id, ExerciseAttempt.created_at.desc())
        .ext(distinct_on(ExerciseAttempt.exercise_id))
    )
    scores = {row.exercise_id: row.score for row in await session.execute(latest)}
    missing = exercise_ids - scores.keys()
    if missing:
        raise LessonIncompleteError(len(missing))

    now = datetime.now(UTC)
    score = sum(scores[e] for e in exercise_ids) / len(exercise_ids) if exercise_ids else 1.0
    stmt = insert(LessonProgress).values(
        user_id=user_id,
        lesson_id=lesson.id,
        status=LessonStatus.COMPLETED,
        score=score,
        started_at=now,
        completed_at=now,
    )
    progress = await session.scalar(
        stmt.on_conflict_do_update(
            index_elements=[LessonProgress.user_id, LessonProgress.lesson_id],
            set_={"status": LessonStatus.COMPLETED, "score": score, "completed_at": now},
        ).returning(LessonProgress),
        execution_options={"populate_existing": True},
    )
    assert progress is not None  # noqa: S101 - an upsert with RETURNING always yields a row
    await session.commit()
    return progress, lesson


async def get_progress(
    session: AsyncSession, user_id: uuid.UUID
) -> tuple[Sequence[LessonProgress], Sequence[ObjectiveMastery]]:
    lessons = await session.scalars(
        select(LessonProgress)
        .where(LessonProgress.user_id == user_id)
        .options(selectinload(LessonProgress.lesson))
        .order_by(LessonProgress.started_at)
    )
    objectives = await session.scalars(
        select(ObjectiveMastery)
        .where(ObjectiveMastery.user_id == user_id)
        .options(selectinload(ObjectiveMastery.objective))
        .order_by(ObjectiveMastery.mastery, ObjectiveMastery.last_seen_at.desc())
    )
    return lessons.all(), objectives.all()
