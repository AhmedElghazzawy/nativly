"""Import curriculum YAML into the database.

    uv run python -m app.learning.importer ../content        (local, from api/)
    python -m app.learning.importer content                  (container, on start)

Validates every file first, then upserts by slug in a single transaction, so a bad file
never leaves the curriculum half-imported. Re-running with unchanged content is a no-op.
Lesson steps and lesson↔objective links are replaced per lesson; exercises and objectives
are only ever updated, never deleted, so learner history pointing at them stays valid.
"""

import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import create_engine, create_sessionmaker
from app.learning.content import CourseDef, ExerciseDef, ExerciseStepDef, UnitDef
from app.learning.models import (
    Course,
    Exercise,
    LearningObjective,
    Lesson,
    LessonStep,
    StepKind,
    Unit,
)
from app.vocab.content import DeckDef
from app.vocab.importer import import_deck


class ContentError(Exception):
    """Content is invalid; the message lists every problem found."""


@dataclass
class CourseBundle:
    path: Path
    course: CourseDef
    units: list[UnitDef]
    decks: list[DeckDef] = field(default_factory=list)


@dataclass
class ImportReport:
    courses: int = 0
    units: int = 0
    lessons: int = 0
    exercises: int = 0
    objectives: int = 0
    decks: int = 0
    vocab_items: int = 0
    created: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"{self.courses} course(s), {self.units} unit(s), {self.lessons} lesson(s), "
            f"{self.exercises} exercise(s), {self.objectives} objective(s), "
            f"{self.decks} deck(s) with {self.vocab_items} word(s); "
            f"{len(self.created)} new"
        )


def _read_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_content(root: Path) -> list[CourseBundle]:
    """Parse and cross-validate all content under `root`. Raises ContentError."""
    if not root.is_dir():
        raise ContentError(f"content directory not found: {root}")

    errors: list[str] = []
    bundles: list[CourseBundle] = []
    for course_file in sorted(root.glob("*/*/course.yaml")):
        try:
            course = CourseDef.model_validate(_read_yaml(course_file))
        except (ValidationError, yaml.YAMLError) as exc:
            errors.append(f"{course_file}: {exc}")
            continue
        units: list[UnitDef] = []
        for unit_file in sorted((course_file.parent / "units").glob("*.yaml")):
            try:
                units.append(UnitDef.model_validate(_read_yaml(unit_file)))
            except (ValidationError, yaml.YAMLError) as exc:
                errors.append(f"{unit_file}: {exc}")
        decks: list[DeckDef] = []
        for deck_file in sorted((course_file.parent / "decks").glob("*.yaml")):
            try:
                decks.append(DeckDef.model_validate(_read_yaml(deck_file)))
            except (ValidationError, yaml.YAMLError) as exc:
                errors.append(f"{deck_file}: {exc}")
        bundles.append(CourseBundle(course_file, course, units, decks))

    if not errors:
        errors.extend(_cross_check(bundles))
    if errors:
        raise ContentError("\n".join(errors))
    return bundles


def _cross_check(bundles: list[CourseBundle]) -> list[str]:
    errors: list[str] = []
    seen: dict[str, str] = {}

    def claim(kind: str, slug: str, where: str) -> None:
        key = f"{kind}:{slug}"
        if key in seen:
            errors.append(f"duplicate {kind} slug '{slug}' in {where} (also in {seen[key]})")
        seen[key] = where

    for bundle in bundles:
        where = str(bundle.path.parent)
        claim("course", bundle.course.slug, where)
        objectives = {o.slug for o in bundle.course.objectives}
        for o in bundle.course.objectives:
            claim("objective", o.slug, where)
        positions = [u.position for u in bundle.units]
        if len(positions) != len(set(positions)):
            errors.append(f"{where}: two units share a position")
        for unit in bundle.units:
            claim("unit", unit.slug, where)
            for lesson in unit.lessons:
                claim("lesson", lesson.slug, where)
                for slug in lesson.objectives:
                    if slug not in objectives:
                        errors.append(f"lesson '{lesson.slug}': unknown objective '{slug}'")
                for step in lesson.steps:
                    if isinstance(step, ExerciseStepDef):
                        ex = step.exercise
                        claim("exercise", ex.slug, where)
                        if ex.objective not in objectives:
                            errors.append(f"exercise '{ex.slug}': unknown objective")
        units = {u.slug for u in bundle.units}
        for deck in bundle.decks:
            claim("deck", deck.slug, where)
            if deck.unit is not None and deck.unit not in units:
                errors.append(f"deck '{deck.slug}': unknown unit '{deck.unit}'")
            for item in deck.items:
                claim("vocab item", item.slug, where)
    return errors


async def _upsert[M: (Course, Unit, Lesson, LearningObjective, Exercise)](
    session: AsyncSession, model: type[M], slug: str, report: ImportReport, **values: Any
) -> M:
    obj = await session.scalar(select(model).where(model.slug == slug))
    if obj is None:
        obj = model(slug=slug, **values)
        session.add(obj)
        report.created.append(f"{model.__tablename__}:{slug}")
    else:
        for key, value in values.items():
            setattr(obj, key, value)
    await session.flush()
    return obj


async def import_content(session: AsyncSession, root: Path) -> ImportReport:
    bundles = load_content(root)
    report = ImportReport()

    for bundle in bundles:
        c = bundle.course
        course = await _upsert(
            session, Course, c.slug, report,
            language=c.language, cefr_level=c.cefr_level, title=c.title,
            description=c.description,
        )  # fmt: skip
        report.courses += 1

        objectives: dict[str, LearningObjective] = {}
        for o in c.objectives:
            objectives[o.slug] = await _upsert(
                session, LearningObjective, o.slug, report,
                language=c.language, cefr_level=c.cefr_level, skill=o.skill,
                can_do=o.can_do, grammar_point=o.grammar_point,
            )  # fmt: skip
            report.objectives += 1

        unit_ids = {}
        for u in bundle.units:
            unit = await _upsert(
                session, Unit, u.slug, report,
                course_id=course.id, position=u.position, title=u.title,
                description=u.description,
            )  # fmt: skip
            report.units += 1
            unit_ids[u.slug] = unit.id

            for position, lesson_def in enumerate(u.lessons, start=1):
                lesson = await _upsert(
                    session, Lesson, lesson_def.slug, report,
                    unit_id=unit.id, position=position, title=lesson_def.title,
                    summary=lesson_def.summary,
                    estimated_minutes=lesson_def.estimated_minutes,
                )  # fmt: skip
                report.lessons += 1
                await session.refresh(lesson, ["objectives"])
                lesson.objectives = [objectives[s] for s in lesson_def.objectives]

                await session.execute(delete(LessonStep).where(LessonStep.lesson_id == lesson.id))
                for step_position, step in enumerate(lesson_def.steps, start=1):
                    if isinstance(step, ExerciseStepDef):
                        exercise = await _upsert_exercise(
                            session, step.exercise, objectives, report
                        )
                        session.add(
                            LessonStep(
                                lesson_id=lesson.id, position=step_position,
                                kind=StepKind.EXERCISE, exercise_id=exercise.id,
                            )
                        )  # fmt: skip
                    else:
                        session.add(
                            LessonStep(
                                lesson_id=lesson.id, position=step_position,
                                kind=StepKind.EXPLAIN, title=step.title, body=step.body,
                            )
                        )  # fmt: skip
                await session.flush()

        for deck_def in bundle.decks:
            count, created = await import_deck(
                session, deck_def, c.language, c.cefr_level, unit_ids
            )
            report.decks += 1
            report.vocab_items += count
            report.created.extend(created)

    await session.commit()
    return report


async def _upsert_exercise(
    session: AsyncSession,
    ex: ExerciseDef,
    objectives: dict[str, LearningObjective],
    report: ImportReport,
) -> Exercise:
    payload, answer = ex.split()
    exercise = await _upsert(
        session, Exercise, ex.slug, report,
        objective_id=objectives[ex.objective].id, type=ex.type, difficulty=ex.difficulty,
        payload=payload, answer=answer,
    )  # fmt: skip
    report.exercises += 1
    return exercise


async def _main(root: Path) -> int:
    settings = get_settings()
    engine = create_engine(settings)
    try:
        async with create_sessionmaker(engine)() as session:
            report = await import_content(session, root)
    except ContentError as exc:
        print(f"Content is invalid; nothing was imported:\n{exc}", file=sys.stderr)
        return 1
    finally:
        await engine.dispose()
    print(f"Imported {report}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m app.learning.importer <content-dir>", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(_main(Path(sys.argv[1]))))
