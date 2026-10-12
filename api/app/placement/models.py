"""Adaptive placement: an item bank (content), test sessions and responses, per-skill levels."""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin, str_enum
from app.learning.models import CefrLevel, Skill


class SessionStatus(enum.StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class PlacementItem(TimestampMixin, Base):
    __tablename__ = "placement_items"
    __table_args__ = (Index("ix_placement_items_skill_level", "skill", "cefr_level"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    language: Mapped[str] = mapped_column(String(8))
    skill: Mapped[Skill] = mapped_column(str_enum(Skill, "skill"))
    cefr_level: Mapped[CefrLevel] = mapped_column(str_enum(CefrLevel, "cefr_level"))
    passage: Mapped[str | None] = mapped_column(Text)  # reading items
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list[str]] = mapped_column(JSONB)
    answer: Mapped[int] = mapped_column(SmallInteger)  # never sent to clients


class PlacementSession(Base):
    __tablename__ = "placement_sessions"
    __table_args__ = (Index("ix_placement_sessions_user_status", "user_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    language: Mapped[str] = mapped_column(String(8))
    status: Mapped[SessionStatus] = mapped_column(str_enum(SessionStatus, "session_status"))
    # Staircase state per skill: {"grammar": {"level": 2, "asked": 3}, ...}
    state: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # The question the server is waiting for: answers to anything else are rejected.
    pending_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("placement_items.id", ondelete="SET NULL")
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlacementResponse(Base):
    __tablename__ = "placement_responses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("placement_sessions.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("placement_items.id", ondelete="RESTRICT")
    )
    skill: Mapped[Skill] = mapped_column(str_enum(Skill, "skill"))
    cefr_level: Mapped[CefrLevel] = mapped_column(str_enum(CefrLevel, "cefr_level"))
    choice: Mapped[int] = mapped_column(SmallInteger)
    is_correct: Mapped[bool]
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SkillLevel(Base):
    """The learner's current level per skill. Placement sets it; practice will refine it."""

    __tablename__ = "skill_levels"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    skill: Mapped[Skill] = mapped_column(str_enum(Skill, "skill"), primary_key=True)
    cefr_level: Mapped[CefrLevel] = mapped_column(str_enum(CefrLevel, "cefr_level"))
    score: Mapped[int] = mapped_column(SmallInteger)  # 0-100 within the level
    source: Mapped[str] = mapped_column(String(20))  # placement | practice
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
