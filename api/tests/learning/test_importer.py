from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning.importer import ContentError, import_content, load_content
from app.learning.models import Exercise, Lesson, LessonStep, StepKind
from tests.learning.conftest import REPO_CONTENT, ContentDir, course_yaml, unit_yaml


async def count(session: AsyncSession, model: Any) -> int:
    return await session.scalar(select(func.count()).select_from(model)) or 0


def test_repository_content_is_valid() -> None:
    # Guards every content change in CI: the real curriculum must always import.
    bundles = load_content(REPO_CONTENT)

    assert bundles, "expected at least one course under content/"


async def test_import_creates_curriculum(session: AsyncSession, content: ContentDir) -> None:
    report = await import_content(session, content.write())

    assert (report.courses, report.units, report.lessons) == (1, 1, 1)
    assert report.exercises == 3
    lesson = await session.scalar(select(Lesson).where(Lesson.slug == "lesson-1"))
    assert lesson is not None
    await session.refresh(lesson, ["steps", "objectives"])
    assert [s.kind for s in lesson.steps] == [
        StepKind.EXPLAIN,
        StepKind.EXERCISE,
        StepKind.EXERCISE,
        StepKind.EXERCISE,
    ]
    assert [o.slug for o in lesson.objectives] == ["obj-past"]


async def test_import_is_idempotent(session: AsyncSession, content: ContentDir) -> None:
    root = content.write()
    await import_content(session, root)

    second = await import_content(session, root)

    assert second.created == []
    assert await count(session, Exercise) == 3
    assert await count(session, LessonStep) == 4


async def test_reimport_applies_edits_and_replaces_steps(
    session: AsyncSession, content: ContentDir
) -> None:
    await import_content(session, content.write())
    unit = unit_yaml()
    lesson = unit["lessons"][0]
    lesson["title"] = "Renamed lesson"
    lesson["steps"] = lesson["steps"][:2]  # drop the cloze and reorder steps

    await import_content(session, content.write(units=[unit]))

    updated = await session.scalar(select(Lesson).where(Lesson.slug == "lesson-1"))
    assert updated is not None
    assert updated.title == "Renamed lesson"
    assert await count(session, LessonStep) == 2
    # Exercises are never deleted: future attempts will reference them.
    assert await count(session, Exercise) == 3


async def test_exercise_answers_are_stored_apart_from_payload(
    session: AsyncSession, content: ContentDir
) -> None:
    await import_content(session, content.write())

    mcq = await session.scalar(select(Exercise).where(Exercise.slug == "ex-mcq"))
    reorder = await session.scalar(select(Exercise).where(Exercise.slug == "ex-reorder"))

    assert mcq is not None and reorder is not None
    assert mcq.payload == {"prompt": "Pick one", "options": ["walk", "walked"]}
    assert mcq.answer == {"correct": 1, "explanation": "Add -ed."}
    assert sorted(reorder.payload["tokens"]) == sorted(reorder.answer["sequence"])
    assert reorder.payload["tokens"] != reorder.answer["sequence"]


def _bad_mcq(**changes: Any) -> dict[str, Any]:
    unit = unit_yaml()
    unit["lessons"][0]["steps"][1]["exercise"] |= changes
    return unit


@pytest.mark.parametrize(
    ("units", "message"),
    [
        (
            [unit_yaml(lessons=[unit_yaml()["lessons"][0] | {"objectives": ["nope"]}])],
            "unknown objective 'nope'",
        ),
        ([_bad_mcq(answer=5)], "out of range"),
        ([_bad_mcq(objective="nope")], "unknown objective"),
        ([_bad_mcq(explaination="typo")], "Extra inputs are not permitted"),
        ([unit_yaml(), unit_yaml(position=2)], "duplicate unit slug 'unit-1'"),
    ],
)
async def test_invalid_content_is_rejected_and_nothing_written(
    session: AsyncSession, content: ContentDir, units: list[dict[str, Any]], message: str
) -> None:
    root = content.write(units=units)

    with pytest.raises(ContentError, match=message):
        await import_content(session, root)

    assert await count(session, Exercise) == 0


def test_cloze_blank_count_must_match_answers(content: ContentDir) -> None:
    unit = unit_yaml()
    unit["lessons"][0]["steps"][2]["exercise"]["text"] = "I ___ home ___."
    root = content.write(units=[unit])

    with pytest.raises(ContentError, match="2 blank"):
        load_content(root)


def test_course_file_must_be_valid(content: ContentDir) -> None:
    root = content.write(course=course_yaml(cefr_level="Z9"))

    with pytest.raises(ContentError, match="cefr_level"):
        load_content(root)


def test_missing_content_directory(tmp_path: Path) -> None:
    with pytest.raises(ContentError, match="not found"):
        load_content(tmp_path / "missing")
