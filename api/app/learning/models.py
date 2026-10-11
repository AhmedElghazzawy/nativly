"""Curriculum: course → unit → lesson → step, plus objectives and exercises.

Content is authored as YAML (see `content/`) and imported by slug, so slugs are the stable
identity across re-imports; UUIDs are internal.
"""

import enum
import uuid
from typing import Any

from sqlalchemy import Column, Enum, ForeignKey, SmallInteger, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin


class CefrLevel(enum.StrEnum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class Skill(enum.StrEnum):
    READING = "reading"
    LISTENING = "listening"
    WRITING = "writing"
    SPEAKING = "speaking"
    GRAMMAR = "grammar"
    VOCAB = "vocab"


class StepKind(enum.StrEnum):
    EXPLAIN = "explain"
    EXERCISE = "exercise"
    LISTENING = "listening"
    WRITING = "writing"
    SPEAKING = "speaking"
    REVIEW = "review"


class ExerciseType(enum.StrEnum):
    MCQ = "mcq"
    CLOZE = "cloze"
    REORDER = "reorder"


def _str_enum(enum_cls: type[enum.StrEnum], name: str) -> Enum:
    # VARCHAR + CHECK instead of a native Postgres ENUM: adding a value later is a one-line
    # constraint change rather than an ALTER TYPE that can't run inside a transaction.
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda e: [m.value for m in e],
    )


lesson_objectives = Table(
    "lesson_objectives",
    Base.metadata,
    Column("lesson_id", ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "objective_id", ForeignKey("learning_objectives.id", ondelete="CASCADE"), primary_key=True
    ),
)


class Course(TimestampMixin, Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    language: Mapped[str] = mapped_column(String(8))
    cefr_level: Mapped[CefrLevel] = mapped_column(_str_enum(CefrLevel, "cefr_level"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")

    units: Mapped[list["Unit"]] = relationship(
        back_populates="course", order_by="Unit.position", cascade="all, delete-orphan"
    )


class Unit(TimestampMixin, Base):
    __tablename__ = "units"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    position: Mapped[int] = mapped_column(SmallInteger)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")

    course: Mapped[Course] = relationship(back_populates="units")
    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="unit", order_by="Lesson.position", cascade="all, delete-orphan"
    )


class LearningObjective(TimestampMixin, Base):
    __tablename__ = "learning_objectives"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    language: Mapped[str] = mapped_column(String(8))
    cefr_level: Mapped[CefrLevel] = mapped_column(_str_enum(CefrLevel, "cefr_level"))
    skill: Mapped[Skill] = mapped_column(_str_enum(Skill, "skill"))
    can_do: Mapped[str] = mapped_column(Text)
    grammar_point: Mapped[str | None] = mapped_column(String(200))


class Lesson(TimestampMixin, Base):
    __tablename__ = "lessons"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("units.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    position: Mapped[int] = mapped_column(SmallInteger)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="")
    estimated_minutes: Mapped[int] = mapped_column(SmallInteger)

    unit: Mapped[Unit] = relationship(back_populates="lessons")
    objectives: Mapped[list[LearningObjective]] = relationship(secondary=lesson_objectives)
    steps: Mapped[list["LessonStep"]] = relationship(
        back_populates="lesson", order_by="LessonStep.position", cascade="all, delete-orphan"
    )


class Exercise(TimestampMixin, Base):
    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    objective_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("learning_objectives.id", ondelete="RESTRICT"), index=True
    )
    type: Mapped[ExerciseType] = mapped_column(_str_enum(ExerciseType, "exercise_type"))
    difficulty: Mapped[int] = mapped_column(SmallInteger)
    # What the learner sees (safe to send to clients).
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # Answer key and explanation: never serialized to clients before an attempt.
    answer: Mapped[dict[str, Any]] = mapped_column(JSONB)

    objective: Mapped[LearningObjective] = relationship()


class LessonStep(Base):
    __tablename__ = "lesson_steps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(SmallInteger)
    kind: Mapped[StepKind] = mapped_column(_str_enum(StepKind, "step_kind"))
    title: Mapped[str | None] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(Text)  # Markdown
    exercise_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"), index=True
    )

    lesson: Mapped[Lesson] = relationship(back_populates="steps")
    exercise: Mapped[Exercise | None] = relationship()
