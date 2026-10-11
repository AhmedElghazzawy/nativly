"""Decks, the daily review queue and reviews for a learner."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fsrs import Rating
from sqlalchemy import and_, exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning.service import NotFoundError
from app.vocab import srs
from app.vocab.models import (
    CardState,
    Deck,
    DeckSubscription,
    Review,
    UserCard,
    VocabItem,
    deck_items,
)

# A card counts as "mature" once FSRS expects it to survive three weeks (Anki's convention).
MATURE_STABILITY_DAYS = 21.0


@dataclass(frozen=True)
class DeckStats:
    deck: Deck
    total: int
    studied: int
    subscribed: bool


@dataclass(frozen=True)
class QueueEntry:
    item: VocabItem
    card: UserCard | None  # None: a new word, introduced on its first review


@dataclass(frozen=True)
class ReviewOutcome:
    card: UserCard


@dataclass(frozen=True)
class Summary:
    due_now: int
    new_available_today: int
    reviewed_today: int
    streak_days: int
    total_cards: int
    mature_cards: int


def start_of_day(now: datetime, tz: ZoneInfo) -> datetime:
    return datetime.combine(now.astimezone(tz).date(), time.min, tzinfo=tz)


async def list_decks(session: AsyncSession, user_id: uuid.UUID) -> list[DeckStats]:
    total = func.count(deck_items.c.item_id)
    studied = func.count(deck_items.c.item_id).filter(
        exists().where(UserCard.user_id == user_id, UserCard.item_id == deck_items.c.item_id)
    )
    subscribed = exists().where(
        DeckSubscription.user_id == user_id, DeckSubscription.deck_id == Deck.id
    )
    rows = await session.execute(
        select(Deck, total, studied, subscribed)
        .join(deck_items, deck_items.c.deck_id == Deck.id)
        .group_by(Deck.id)
        .order_by(Deck.cefr_level, Deck.title)
    )
    return [DeckStats(deck, t, s, sub) for deck, t, s, sub in rows]


async def get_deck(session: AsyncSession, user_id: uuid.UUID, slug: str) -> DeckStats:
    for stats in await list_decks(session, user_id):
        if stats.deck.slug == slug:
            return stats
    raise NotFoundError


async def deck_items_with_cards(
    session: AsyncSession, user_id: uuid.UUID, deck: Deck
) -> list[tuple[VocabItem, UserCard | None]]:
    rows = await session.execute(
        select(VocabItem, UserCard)
        .join(deck_items, deck_items.c.item_id == VocabItem.id)
        .outerjoin(UserCard, and_(UserCard.item_id == VocabItem.id, UserCard.user_id == user_id))
        .where(deck_items.c.deck_id == deck.id)
        .order_by(deck_items.c.position)
    )
    return [(item, card) for item, card in rows]


async def subscribe(session: AsyncSession, user_id: uuid.UUID, slug: str) -> None:
    deck_id = await session.scalar(select(Deck.id).where(Deck.slug == slug))
    if deck_id is None:
        raise NotFoundError
    await session.execute(
        insert(DeckSubscription).values(user_id=user_id, deck_id=deck_id).on_conflict_do_nothing()
    )
    await session.commit()


async def unsubscribe(session: AsyncSession, user_id: uuid.UUID, slug: str) -> None:
    deck_id = await session.scalar(select(Deck.id).where(Deck.slug == slug))
    if deck_id is None:
        raise NotFoundError
    subscription = await session.get(DeckSubscription, (user_id, deck_id))
    if subscription is not None:
        await session.delete(subscription)  # existing cards keep their schedule
        await session.commit()


async def _introduced_since(session: AsyncSession, user_id: uuid.UUID, since: datetime) -> int:
    count = await session.scalar(
        select(func.count())
        .select_from(UserCard)
        .where(UserCard.user_id == user_id, UserCard.created_at >= since)
    )
    return count or 0


async def queue(
    session: AsyncSession,
    user_id: uuid.UUID,
    now: datetime,
    tz: ZoneInfo,
    limit: int,
    new_per_day: int,
) -> list[QueueEntry]:
    """Due cards first (most overdue first), then new words up to today's allowance."""
    due_rows = await session.scalars(
        select(UserCard)
        .where(UserCard.user_id == user_id, UserCard.due <= now)
        .order_by(UserCard.due)
        .limit(limit)
    )
    due = list(due_rows.all())
    entries = [QueueEntry(card.item, card) for card in await _with_items(session, due)]

    allowance = new_per_day - await _introduced_since(session, user_id, start_of_day(now, tz))
    room = min(max(allowance, 0), limit - len(entries))
    if room > 0:
        entries.extend(QueueEntry(item, None) for item in await _new_items(session, user_id, room))
    return entries


async def _with_items(session: AsyncSession, cards: list[UserCard]) -> list[UserCard]:
    if cards:
        items = await session.scalars(
            select(VocabItem).where(VocabItem.id.in_([c.item_id for c in cards]))
        )
        by_id = {item.id: item for item in items}
        for card in cards:
            card.item = by_id[card.item_id]
    return cards


async def _new_items(session: AsyncSession, user_id: uuid.UUID, limit: int) -> Sequence[VocabItem]:
    # Words from subscribed decks the learner has never reviewed, in the order the decks were
    # started and the order authors put the words in. An item in two decks appears once.
    has_card = exists().where(UserCard.user_id == user_id, UserCard.item_id == VocabItem.id)
    result = await session.scalars(
        select(VocabItem)
        .join(deck_items, deck_items.c.item_id == VocabItem.id)
        .join(
            DeckSubscription,
            and_(
                DeckSubscription.deck_id == deck_items.c.deck_id,
                DeckSubscription.user_id == user_id,
            ),
        )
        .where(~has_card)
        .group_by(VocabItem.id)
        .order_by(func.min(DeckSubscription.started_at), func.min(deck_items.c.position))
        .limit(limit)
    )
    return result.all()


async def review(
    session: AsyncSession,
    user_id: uuid.UUID,
    item_slug: str,
    rating: Rating,
    duration_ms: int | None,
    now: datetime,
) -> ReviewOutcome:
    item = await session.scalar(select(VocabItem).where(VocabItem.slug == item_slug))
    if item is None:
        raise NotFoundError

    card = await session.scalar(
        select(UserCard)
        .where(UserCard.user_id == user_id, UserCard.item_id == item.id)
        .with_for_update()
    )
    if card is None:
        # Only words from decks the learner studies can be introduced.
        in_subscribed_deck = await session.scalar(
            select(
                exists().where(
                    deck_items.c.item_id == item.id,
                    DeckSubscription.deck_id == deck_items.c.deck_id,
                    DeckSubscription.user_id == user_id,
                )
            )
        )
        if not in_subscribed_deck:
            raise NotFoundError
        card = await _create_card(session, user_id, item.id, now)

    state_before = card.state if card.reps else None
    scheduled = srs.schedule(card if card.reps else None, rating, now, duration_ms)
    srs.apply(card, scheduled, rating)
    session.add(
        Review(
            card_id=card.id,
            user_id=user_id,
            rating=int(rating),
            reviewed_at=now,
            duration_ms=duration_ms,
            state_before=state_before,
            due_after=card.due,
        )
    )
    await session.commit()
    card.item = item
    return ReviewOutcome(card)


async def _create_card(
    session: AsyncSession, user_id: uuid.UUID, item_id: uuid.UUID, now: datetime
) -> UserCard:
    # Two tabs can introduce the same word at once: let the unique constraint decide, then lock.
    await session.execute(
        insert(UserCard)
        .values(
            id=uuid.uuid4(),
            user_id=user_id,
            item_id=item_id,
            state=int(CardState.LEARNING),
            due=now,
            reps=0,
            lapses=0,
            created_at=now,
        )
        .on_conflict_do_nothing(index_elements=["user_id", "item_id"])
    )
    card = await session.scalar(
        select(UserCard)
        .where(UserCard.user_id == user_id, UserCard.item_id == item_id)
        .with_for_update()
    )
    assert card is not None  # noqa: S101 - inserted or already present
    return card


async def summary(
    session: AsyncSession, user_id: uuid.UUID, now: datetime, tz: ZoneInfo, new_per_day: int
) -> Summary:
    today_start = start_of_day(now, tz)
    due_now = await session.scalar(
        select(func.count())
        .select_from(UserCard)
        .where(UserCard.user_id == user_id, UserCard.due <= now)
    )
    totals = (
        await session.execute(
            select(
                func.count(),
                func.count().filter(UserCard.stability >= MATURE_STABILITY_DAYS),
            ).where(UserCard.user_id == user_id)
        )
    ).one()
    reviewed_today = await session.scalar(
        select(func.count())
        .select_from(Review)
        .where(Review.user_id == user_id, Review.reviewed_at >= today_start)
    )
    unseen = len(await _new_items(session, user_id, new_per_day))
    allowance = max(new_per_day - await _introduced_since(session, user_id, today_start), 0)
    return Summary(
        due_now=due_now or 0,
        new_available_today=min(unseen, allowance),
        reviewed_today=reviewed_today or 0,
        streak_days=await _streak(session, user_id, now, tz),
        total_cards=totals[0],
        mature_cards=totals[1],
    )


async def _streak(session: AsyncSession, user_id: uuid.UUID, now: datetime, tz: ZoneInfo) -> int:
    """Consecutive local days with at least one review, ending today (or yesterday)."""
    local_day = func.date(func.timezone(str(tz), Review.reviewed_at))
    rows = await session.scalars(
        select(local_day)
        .where(Review.user_id == user_id, Review.reviewed_at >= now - timedelta(days=400))
        .group_by(local_day)
        .order_by(local_day.desc())
    )
    days: list[date] = list(rows.all())
    today = now.astimezone(tz).date()
    expected = today if days and days[0] == today else today - timedelta(days=1)
    streak = 0
    for day in days:
        if day != expected:
            break
        streak += 1
        expected -= timedelta(days=1)
    return streak
