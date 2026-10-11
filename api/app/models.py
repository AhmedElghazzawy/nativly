"""Imports every ORM model so Base.metadata is complete (used by Alembic and test setup)."""

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

__all__ = [
    "Base",
    "Course",
    "Deck",
    "DeckSubscription",
    "Exercise",
    "ExerciseAttempt",
    "LearningObjective",
    "Lesson",
    "LessonProgress",
    "LessonStep",
    "ObjectiveMastery",
    "RefreshToken",
    "Review",
    "Unit",
    "User",
    "UserCard",
    "VocabItem",
    "deck_items",
    "lesson_objectives",
]
