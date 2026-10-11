from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.learning.models import CefrLevel, LessonStatus, Skill, StepKind


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


# --- Attempts and progress -----------------------------------------------------------------


class McqResponse(BaseModel):
    type: Literal["mcq"]
    choice: int = Field(ge=0)


class ClozeResponse(BaseModel):
    type: Literal["cloze"]
    blanks: list[Annotated[str, Field(max_length=200)]] = Field(min_length=1, max_length=20)


class ReorderResponse(BaseModel):
    type: Literal["reorder"]
    sequence: list[Annotated[str, Field(max_length=100)]] = Field(min_length=2, max_length=50)


ExerciseResponse = Annotated[
    McqResponse | ClozeResponse | ReorderResponse, Field(discriminator="type")
]


class AttemptRequest(BaseModel):
    response: ExerciseResponse
    lesson_slug: str | None = Field(
        default=None, description="Lesson the exercise was done in; records lesson progress"
    )
    duration_ms: int | None = Field(default=None, ge=0, le=3_600_000)


class MasteryRead(BaseModel):
    objective_slug: str
    mastery: float


class AttemptResult(BaseModel):
    is_correct: bool
    score: float
    correct_answer: int | list[str] = Field(
        description="mcq: option index · cloze: one accepted answer per blank · reorder: tokens"
    )
    explanation: str
    mastery: MasteryRead


class LessonProgressRead(BaseModel):
    lesson_slug: str
    title: str
    status: LessonStatus
    score: float | None
    started_at: datetime
    completed_at: datetime | None


class ObjectiveProgressRead(BaseModel):
    slug: str
    skill: Skill
    can_do: str
    mastery: float
    evidence_count: int
    last_seen_at: datetime


class ProgressRead(BaseModel):
    lessons: list[LessonProgressRead]
    objectives: list[ObjectiveProgressRead] = Field(description="Weakest first")
