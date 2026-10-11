"""Vocabulary decks and spaced repetition (FSRS).

Items and decks are content (imported from YAML by slug). Cards and reviews are per learner:
a card is created the first time a learner reviews an item, and holds its FSRS memory state.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, str_enum
from app.learning.models import CefrLevel


class PartOfSpeech(enum.StrEnum):
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PREPOSITION = "preposition"
    PHRASE = "phrase"
    OTHER = "other"


class CardState(enum.IntEnum):
    # Mirrors fsrs.State so values round-trip without translation.
    LEARNING = 1
    REVIEW = 2
    RELEARNING = 3


deck_items = Table(
    "deck_items",
    Base.metadata,
    Column("deck_id", ForeignKey("decks.id", ondelete="CASCADE"), primary_key=True),
    Column("item_id", ForeignKey("vocab_items.id", ondelete="CASCADE"), primary_key=True),
    Column("position", SmallInteger, nullable=False),
)


class VocabItem(TimestampMixin, Base):
    __tablename__ = "vocab_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    language: Mapped[str] = mapped_column(String(8))
    cefr_level: Mapped[CefrLevel] = mapped_column(str_enum(CefrLevel, "cefr_level"))
    lemma: Mapped[str] = mapped_column(String(100))
    part_of_speech: Mapped[PartOfSpeech] = mapped_column(str_enum(PartOfSpeech, "part_of_speech"))
    definition: Mapped[str] = mapped_column(Text)
    examples: Mapped[list[str]] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)  # e.g. irregular forms: go - went - gone


class Deck(TimestampMixin, Base):
    __tablename__ = "decks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    language: Mapped[str] = mapped_column(String(8))
    cefr_level: Mapped[CefrLevel] = mapped_column(str_enum(CefrLevel, "cefr_level"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    # The unit this deck supports, if any: lets the course suggest it at the right time.
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("units.id", ondelete="SET NULL"), index=True
    )

    items: Mapped[list[VocabItem]] = relationship(
        secondary=deck_items, order_by=deck_items.c.position
    )


class DeckSubscription(Base):
    """A learner studying a deck: its items enter their daily queue as new cards."""

    __tablename__ = "deck_subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    deck_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("decks.id", ondelete="CASCADE"), primary_key=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserCard(Base):
    __tablename__ = "user_cards"
    __table_args__ = (
        UniqueConstraint("user_id", "item_id"),
        # The review queue: "this learner's cards that are due", oldest first.
        Index("ix_user_cards_user_due", "user_id", "due"),
        CheckConstraint("state IN (1, 2, 3)", name="state"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vocab_items.id", ondelete="CASCADE"), index=True
    )
    # FSRS memory state (see fsrs.Card).
    state: Mapped[int] = mapped_column(SmallInteger)
    step: Mapped[int | None] = mapped_column(SmallInteger)
    stability: Mapped[float | None] = mapped_column(Float)
    difficulty: Mapped[float | None] = mapped_column(Float)
    due: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_review: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reps: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    item: Mapped[VocabItem] = relationship()


class Review(Base):
    """Every rating, kept so FSRS parameters can later be optimized per learner."""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 4", name="rating"),
        Index("ix_reviews_user_reviewed_at", "user_id", "reviewed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    card_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_cards.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    rating: Mapped[int] = mapped_column(SmallInteger)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    state_before: Mapped[int | None] = mapped_column(SmallInteger)
    due_after: Mapped[datetime] = mapped_column(DateTime(timezone=True))
