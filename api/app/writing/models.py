"""Writing tasks (content), learners' submissions with AI feedback, and the mistake log."""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, str_enum
from app.learning.models import CefrLevel, LearningObjective


class MistakeCategory(enum.StrEnum):
    GRAMMAR = "grammar"
    VOCABULARY = "vocabulary"
    SPELLING = "spelling"
    PUNCTUATION = "punctuation"
    WORD_ORDER = "word_order"
    STYLE = "style"


class WritingTask(TimestampMixin, Base):
    __tablename__ = "writing_tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    objective_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("learning_objectives.id", ondelete="RESTRICT"), index=True
    )
    cefr_level: Mapped[CefrLevel] = mapped_column(str_enum(CefrLevel, "cefr_level"))
    prompt: Mapped[str] = mapped_column(Text)
    guidance: Mapped[list[str]] = mapped_column(JSONB)  # bullet points: what to include
    min_words: Mapped[int] = mapped_column(SmallInteger)
    max_words: Mapped[int] = mapped_column(SmallInteger)

    objective: Mapped[LearningObjective] = relationship()


class WritingSubmission(Base):
    __tablename__ = "writing_submissions"
    __table_args__ = (Index("ix_writing_submissions_user_task", "user_id", "task_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("writing_tasks.id", ondelete="RESTRICT"))
    text: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int] = mapped_column(Integer)
    feedback: Mapped[dict[str, Any]] = mapped_column(JSONB)
    cefr_estimate: Mapped[CefrLevel] = mapped_column(str_enum(CefrLevel, "cefr_level"))
    prompt_version: Mapped[str] = mapped_column(String(50))
    llm_call_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("llm_calls.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Mistake(Base):
    """A learner's recurring error. The same correction seen again bumps `count`."""

    __tablename__ = "mistakes"
    __table_args__ = (Index("uq_mistakes_user_key", "user_id", "key", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # Normalized "original -> correction", so "I have 25 years" and "i have 25 years" match.
    key: Mapped[str] = mapped_column(String(400))
    category: Mapped[MistakeCategory] = mapped_column(str_enum(MistakeCategory, "mistake_category"))
    original: Mapped[str] = mapped_column(String(300))
    correction: Mapped[str] = mapped_column(String(300))
    explanation: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(30))  # writing | tutor | speaking
    count: Mapped[int] = mapped_column(Integer, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
