"""Imports every ORM model so Base.metadata is complete (used by Alembic and test setup)."""

from app.auth.models import RefreshToken, User
from app.core.db import Base
from app.learning.models import (
    Course,
    Exercise,
    LearningObjective,
    Lesson,
    LessonStep,
    Unit,
    lesson_objectives,
)

__all__ = [
    "Base",
    "Course",
    "Exercise",
    "LearningObjective",
    "Lesson",
    "LessonStep",
    "RefreshToken",
    "Unit",
    "User",
    "lesson_objectives",
]
