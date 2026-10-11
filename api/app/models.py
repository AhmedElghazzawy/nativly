"""Imports every ORM model so Base.metadata is complete (used by Alembic and test setup)."""

from app.ai.models import LLMCall
from app.auth.models import RefreshToken, User
from app.core.db import Base
from app.learning.models import (
    Course,
    Exercise,
    ExerciseAttempt,
    LearningObjective,
    Lesson,
    LessonProgress,
    LessonStep,
    ObjectiveMastery,
    Unit,
    lesson_objectives,
)
from app.vocab.models import Deck, DeckSubscription, Review, UserCard, VocabItem, deck_items
from app.writing.models import Mistake, WritingSubmission, WritingTask

__all__ = [
    "Base",
    "Course",
    "Deck",
    "DeckSubscription",
    "Exercise",
    "ExerciseAttempt",
    "LLMCall",
    "LearningObjective",
    "Lesson",
    "LessonProgress",
    "LessonStep",
    "Mistake",
    "ObjectiveMastery",
    "RefreshToken",
    "Review",
    "Unit",
    "User",
    "UserCard",
    "VocabItem",
    "WritingSubmission",
    "WritingTask",
    "deck_items",
    "lesson_objectives",
]
