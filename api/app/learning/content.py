"""Schema for curriculum YAML files in `content/`. Validated before anything touches the DB.

Layout: content/<language>/<level>/course.yaml (course + objectives)
        content/<language>/<level>/units/*.yaml (one unit per file, with its lessons)
"""

import random
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.learning.models import CefrLevel, Skill

Slug = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=100)]
CLOZE_BLANK = "___"


class StrictModel(BaseModel):
    # Typos in content (e.g. `explaination:`) must fail the import, not be silently dropped.
    model_config = ConfigDict(extra="forbid", frozen=True)


class ObjectiveDef(StrictModel):
    slug: Slug
    skill: Skill
    can_do: str = Field(min_length=1)
    grammar_point: str | None = None


class CourseDef(StrictModel):
    slug: Slug
    language: str = Field(pattern=r"^[a-z]{2}$")
    cefr_level: CefrLevel
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    objectives: list[ObjectiveDef] = Field(min_length=1)


class _ExerciseBase(StrictModel):
    slug: Slug
    objective: Slug
    difficulty: int = Field(default=1, ge=1, le=5)
    prompt: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


class McqDef(_ExerciseBase):
    type: Literal["mcq"]
    options: list[str] = Field(min_length=2, max_length=6)
    answer: int = Field(ge=0, description="Index of the correct option")

    @model_validator(mode="after")
    def _answer_in_range(self) -> "McqDef":
        if self.answer >= len(self.options):
            raise ValueError(f"answer index {self.answer} is out of range for {self.slug}")
        if len(set(self.options)) != len(self.options):
            raise ValueError(f"duplicate options in {self.slug}")
        return self

    def split(self) -> tuple[dict[str, Any], dict[str, Any]]:
        return (
            {"prompt": self.prompt, "options": list(self.options)},
            {"correct": self.answer, "explanation": self.explanation},
        )


class ClozeDef(_ExerciseBase):
    type: Literal["cloze"]
    text: str = Field(description=f"Sentence with one {CLOZE_BLANK} per blank")
    answers: list[list[str]] = Field(
        min_length=1, description="Accepted answers per blank, in order"
    )

    @model_validator(mode="after")
    def _blanks_match_answers(self) -> "ClozeDef":
        blanks = self.text.count(CLOZE_BLANK)
        if blanks != len(self.answers):
            raise ValueError(
                f"{self.slug}: {blanks} blank(s) in text but {len(self.answers)} answer list(s)"
            )
        if any(not accepted for accepted in self.answers):
            raise ValueError(f"{self.slug}: every blank needs at least one accepted answer")
        return self

    def split(self) -> tuple[dict[str, Any], dict[str, Any]]:
        return (
            {"prompt": self.prompt, "text": self.text, "blanks": len(self.answers)},
            {"blanks": [list(a) for a in self.answers], "explanation": self.explanation},
        )


class ReorderDef(_ExerciseBase):
    type: Literal["reorder"]
    answer: list[str] = Field(min_length=2, description="Tokens in the correct order")

    def split(self) -> tuple[dict[str, Any], dict[str, Any]]:
        # Shuffle deterministically (seeded by slug) so re-imports don't churn the payload,
        # and never present the tokens already in the correct order.
        tokens = list(self.answer)
        rng = random.Random(self.slug)  # noqa: S311 - not security-sensitive
        while tokens == self.answer and len(set(self.answer)) > 1:
            rng.shuffle(tokens)
        return (
            {"prompt": self.prompt, "tokens": tokens},
            {"sequence": list(self.answer), "explanation": self.explanation},
        )


ExerciseDef = Annotated[McqDef | ClozeDef | ReorderDef, Field(discriminator="type")]


class ExplainStepDef(StrictModel):
    kind: Literal["explain"]
    title: str | None = None
    body: str = Field(min_length=1, description="Markdown")


class ExerciseStepDef(StrictModel):
    kind: Literal["exercise"]
    exercise: ExerciseDef


class WritingTaskDef(StrictModel):
    slug: Slug
    objective: Slug
    prompt: str = Field(min_length=1)
    guidance: list[str] = Field(default_factory=list, max_length=6)
    min_words: int = Field(ge=5, le=500)
    max_words: int = Field(ge=10, le=800)

    @model_validator(mode="after")
    def _range(self) -> "WritingTaskDef":
        if self.max_words <= self.min_words:
            raise ValueError(f"{self.slug}: max_words must be greater than min_words")
        return self


class WritingStepDef(StrictModel):
    kind: Literal["writing"]
    task: WritingTaskDef


StepDef = Annotated[ExplainStepDef | ExerciseStepDef | WritingStepDef, Field(discriminator="kind")]


class LessonDef(StrictModel):
    slug: Slug
    title: str = Field(min_length=1, max_length=200)
    summary: str = ""
    estimated_minutes: int = Field(ge=1, le=120)
    objectives: list[Slug] = Field(min_length=1)
    steps: list[StepDef] = Field(min_length=1)


class UnitDef(StrictModel):
    slug: Slug
    position: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    lessons: list[LessonDef] = Field(min_length=1)
