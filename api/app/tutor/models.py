"""The AI teacher: conversations, messages, and what the teacher remembers about a learner."""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, str_enum


class Speaker(enum.StrEnum):
    LEARNER = "learner"
    TUTOR = "tutor"


class TutorSession(Base):
    __tablename__ = "tutor_sessions"
    __table_args__ = (Index("ix_tutor_sessions_user_started", "user_id", "started_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    mode: Mapped[str] = mapped_column(String(20), default="chat")  # chat | voice (Phase 4)
    title: Mapped[str | None] = mapped_column(String(200))
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TutorMessage(Base):
    __tablename__ = "tutor_messages"
    __table_args__ = (Index("ix_tutor_messages_session_created", "session_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tutor_sessions.id", ondelete="CASCADE")
    )
    speaker: Mapped[Speaker] = mapped_column(str_enum(Speaker, "speaker"))
    text: Mapped[str] = mapped_column(Text)
    # On learner messages: the teacher's gentle corrections of that message.
    corrections: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    llm_call_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("llm_calls.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LearnerFact(Base):
    """Something durable the teacher learned ("works as a nurse"). Learners can delete them."""

    __tablename__ = "learner_facts"
    __table_args__ = (Index("uq_learner_facts_user_key", "user_id", "key", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(300))  # normalized text, for de-duplication
    fact: Mapped[str] = mapped_column(String(300))
    source_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tutor_sessions.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_mentioned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
