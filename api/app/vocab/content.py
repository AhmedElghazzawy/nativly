"""Schema for vocabulary deck YAML: content/<language>/<level>/decks/*.yaml."""

import re

from pydantic import Field, model_validator

from app.learning.content import Slug, StrictModel
from app.vocab.models import PartOfSpeech


class VocabItemDef(StrictModel):
    slug: Slug
    lemma: str = Field(min_length=1, max_length=100)
    part_of_speech: PartOfSpeech
    definition: str = Field(min_length=1, description="Simple English, at or below the level")
    examples: list[str] = Field(min_length=1, max_length=5)
    notes: str | None = None

    @model_validator(mode="after")
    def _examples_use_the_word(self) -> "VocabItemDef":
        # Guards against copy-paste slips: some example must contain the word or one of the
        # forms listed in its notes (irregulars: "make - made - made").
        forms = {self.lemma.lower(), *re.findall(r"[a-z']+", (self.notes or "").lower())}
        examples = " ".join(self.examples).lower()
        if not any(re.search(rf"\b{re.escape(form)}", examples) for form in forms):
            raise ValueError(f"{self.slug}: no example uses '{self.lemma}' or its forms")
        return self


class DeckDef(StrictModel):
    slug: Slug
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    unit: Slug | None = Field(default=None, description="Unit this deck supports")
    items: list[VocabItemDef] = Field(min_length=1)
