from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.learning.models import CefrLevel
from app.vocab.models import PartOfSpeech

RatingName = Literal["again", "hard", "good", "easy"]
CardStatus = Literal["new", "learning", "young", "mature"]


class DeckSummary(BaseModel):
    slug: str
    title: str
    description: str
    cefr_level: CefrLevel
    total: int
    studied: int
    subscribed: bool


class WordRead(BaseModel):
    slug: str
    lemma: str
    part_of_speech: PartOfSpeech
    definition: str
    examples: list[str]
    notes: str | None


class DeckWord(WordRead):
    status: CardStatus
    due: datetime | None


class DeckDetail(DeckSummary):
    words: list[DeckWord]


class Intervals(BaseModel):
    """Seconds until the card returns for each rating, shown on the rating buttons."""

    again: int
    hard: int
    good: int
    easy: int


class QueueCard(BaseModel):
    word: WordRead
    status: CardStatus
    intervals: Intervals


class ReviewRequest(BaseModel):
    rating: RatingName
    duration_ms: int | None = Field(default=None, ge=0, le=3_600_000)


class ReviewResult(BaseModel):
    status: CardStatus
    due: datetime
    interval_seconds: int


class ReviewSummary(BaseModel):
    due_now: int
    new_available_today: int
    reviewed_today: int
    streak_days: int
    total_cards: int
    mature_cards: int
