"""Upsert vocabulary decks; called by the curriculum importer inside its transaction."""

import uuid
from typing import Any

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning.models import CefrLevel
from app.vocab.content import DeckDef
from app.vocab.models import Deck, VocabItem, deck_items


async def import_deck(
    session: AsyncSession,
    deck_def: DeckDef,
    language: str,
    level: CefrLevel,
    unit_ids: dict[str, uuid.UUID],
) -> tuple[int, list[str]]:
    """Returns (item count, slugs of rows created)."""
    created: list[str] = []
    deck = await session.scalar(select(Deck).where(Deck.slug == deck_def.slug))
    values: dict[str, Any] = {
        "language": language,
        "cefr_level": level,
        "title": deck_def.title,
        "description": deck_def.description,
        "unit_id": unit_ids.get(deck_def.unit) if deck_def.unit else None,
    }
    if deck is None:
        deck = Deck(slug=deck_def.slug, **values)
        session.add(deck)
        created.append(f"decks:{deck_def.slug}")
    else:
        for key, value in values.items():
            setattr(deck, key, value)

    item_ids: list[uuid.UUID] = []
    for item_def in deck_def.items:
        item = await session.scalar(select(VocabItem).where(VocabItem.slug == item_def.slug))
        item_values: dict[str, Any] = {
            "language": language,
            "cefr_level": level,
            "lemma": item_def.lemma,
            "part_of_speech": item_def.part_of_speech,
            "definition": item_def.definition,
            "examples": list(item_def.examples),
            "notes": item_def.notes,
        }
        if item is None:
            item = VocabItem(slug=item_def.slug, **item_values)
            session.add(item)
            created.append(f"vocab_items:{item_def.slug}")
        else:
            for key, value in item_values.items():
                setattr(item, key, value)
        await session.flush()
        item_ids.append(item.id)

    # Membership and order are replaced wholesale; items themselves are never deleted
    # (learners' cards point at them).
    await session.flush()
    await session.execute(delete(deck_items).where(deck_items.c.deck_id == deck.id))
    await session.execute(
        insert(deck_items),
        [
            {"deck_id": deck.id, "item_id": item_id, "position": position}
            for position, item_id in enumerate(item_ids, start=1)
        ],
    )
    return len(item_ids), created
