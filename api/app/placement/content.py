"""Schema for the placement item bank: content/<language>/placement/<skill>.yaml."""

from pydantic import Field, model_validator

from app.learning.content import Slug, StrictModel
from app.learning.models import CefrLevel, Skill


class PlacementItemDef(StrictModel):
    slug: Slug
    level: CefrLevel
    passage: str | None = None
    prompt: str = Field(min_length=1)
    options: list[str] = Field(min_length=3, max_length=5)
    answer: int = Field(ge=0)

    @model_validator(mode="after")
    def _valid_answer(self) -> "PlacementItemDef":
        if self.answer >= len(self.options):
            raise ValueError(f"{self.slug}: answer index out of range")
        if len(set(self.options)) != len(self.options):
            raise ValueError(f"{self.slug}: duplicate options")
        return self


class PlacementBankDef(StrictModel):
    skill: Skill
    items: list[PlacementItemDef] = Field(min_length=1)
