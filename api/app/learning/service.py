from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.learning.models import CefrLevel, Course, Lesson, LessonStep, Unit


class NotFoundError(Exception):
    pass


async def list_courses(
    session: AsyncSession, language: str | None = None, level: CefrLevel | None = None
) -> Sequence[Course]:
    query = select(Course).order_by(Course.language, Course.cefr_level)
    if language is not None:
        query = query.where(Course.language == language)
    if level is not None:
        query = query.where(Course.cefr_level == level)
    return (await session.scalars(query)).all()


async def get_course(session: AsyncSession, slug: str) -> Course:
    course = await session.scalar(
        select(Course)
        .where(Course.slug == slug)
        .options(selectinload(Course.units).selectinload(Unit.lessons))
    )
    if course is None:
        raise NotFoundError
    return course


async def get_lesson(session: AsyncSession, slug: str) -> Lesson:
    lesson = await session.scalar(
        select(Lesson)
        .where(Lesson.slug == slug)
        .options(
            selectinload(Lesson.unit).selectinload(Unit.course),
            selectinload(Lesson.objectives),
            selectinload(Lesson.steps).selectinload(LessonStep.exercise),
            selectinload(Lesson.steps).selectinload(LessonStep.writing_task),
        )
    )
    if lesson is None:
        raise NotFoundError
    return lesson
