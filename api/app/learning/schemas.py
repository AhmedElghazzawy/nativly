from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.learning.models import CefrLevel, Skill, StepKind


class CourseSummary(BaseModel):
    slug: str
    language: str
    cefr_level: CefrLevel
    title: str
    description: str


class LessonSummary(BaseModel):
    slug: str
    position: int
    title: str
    summary: str
    estimated_minutes: int


class UnitOutline(BaseModel):
    slug: str
    position: int
    title: str
    description: str
    lessons: list[LessonSummary]


class CourseDetail(CourseSummary):
    units: list[UnitOutline]


class ObjectiveRead(BaseModel):
    slug: str
    skill: Skill
    can_do: str
    grammar_point: str | None


# Public exercise views: what a learner sees before answering. The answer key and the
# explanation live only in `Exercise.answer` and are never part of these models.
class _ExercisePublicBase(BaseModel):
    slug: str
    difficulty: int
    prompt: str


class McqPublic(_ExercisePublicBase):
    type: Literal["mcq"]
    options: list[str]


class ClozePublic(_ExercisePublicBase):
    type: Literal["cloze"]
    text: str
    blanks: int


class ReorderPublic(_ExercisePublicBase):
    type: Literal["reorder"]
    tokens: list[str]


ExercisePublic = Annotated[McqPublic | ClozePublic | ReorderPublic, Field(discriminator="type")]


class StepRead(BaseModel):
    position: int
    kind: StepKind
    title: str | None
    body: str | None
    exercise: ExercisePublic | None


class LessonDetail(LessonSummary):
    course_slug: str
    unit_slug: str
    objectives: list[ObjectiveRead]
    steps: list[StepRead]
