from datetime import UTC, datetime
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fsrs import Rating

from app.auth.dependencies import CurrentUser, SessionDep, SettingsDep
from app.learning.service import NotFoundError
from app.vocab import service, srs
from app.vocab.models import CardState, UserCard, VocabItem
from app.vocab.schemas import (
    CardStatus,
    DeckDetail,
    DeckSummary,
    DeckWord,
    Intervals,
    QueueCard,
    ReviewRequest,
    ReviewResult,
    ReviewSummary,
    WordRead,
)

router = APIRouter(tags=["vocabulary"])

RATINGS = {"again": Rating.Again, "hard": Rating.Hard, "good": Rating.Good, "easy": Rating.Easy}


def learner_timezone(
    tz: Annotated[
        str, Query(max_length=64, description="IANA timezone for 'today', e.g. Europe/Berlin")
    ] = "UTC",
) -> ZoneInfo:
    try:
        return ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown timezone: {tz}"
        ) from None


TimezoneDep = Annotated[ZoneInfo, Depends(learner_timezone)]


def card_status(card: UserCard | None) -> CardStatus:
    if card is None:
        return "new"
    if card.state != CardState.REVIEW:
        return "learning"
    return "mature" if (card.stability or 0) >= service.MATURE_STABILITY_DAYS else "young"


def word(item: VocabItem) -> WordRead:
    return WordRead(
        slug=item.slug,
        lemma=item.lemma,
        part_of_speech=item.part_of_speech,
        definition=item.definition,
        examples=item.examples,
        notes=item.notes,
    )


def deck_summary(stats: service.DeckStats) -> DeckSummary:
    d = stats.deck
    return DeckSummary(
        slug=d.slug,
        title=d.title,
        description=d.description,
        cefr_level=d.cefr_level,
        total=stats.total,
        studied=stats.studied,
        subscribed=stats.subscribed,
    )


@router.get("/decks")
async def list_decks(user: CurrentUser, session: SessionDep) -> list[DeckSummary]:
    return [deck_summary(s) for s in await service.list_decks(session, user.id)]


@router.get("/decks/{slug}")
async def get_deck(slug: str, user: CurrentUser, session: SessionDep) -> DeckDetail:
    try:
        stats = await service.get_deck(session, user.id, slug)
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deck not found") from None
    rows = await service.deck_items_with_cards(session, user.id, stats.deck)
    return DeckDetail(
        **deck_summary(stats).model_dump(),
        words=[
            DeckWord(
                **word(item).model_dump(),
                status=card_status(card),
                due=card.due if card else None,
            )
            for item, card in rows
        ],
    )


@router.put("/decks/{slug}/subscription", status_code=status.HTTP_204_NO_CONTENT)
async def subscribe(slug: str, user: CurrentUser, session: SessionDep) -> None:
    try:
        await service.subscribe(session, user.id, slug)
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deck not found") from None


@router.delete("/decks/{slug}/subscription", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(slug: str, user: CurrentUser, session: SessionDep) -> None:
    try:
        await service.unsubscribe(session, user.id, slug)
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deck not found") from None


@router.get("/review/queue")
async def review_queue(
    user: CurrentUser,
    session: SessionDep,
    settings: SettingsDep,
    tz: TimezoneDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[QueueCard]:
    now = datetime.now(UTC)
    entries = await service.queue(session, user.id, now, tz, limit, settings.new_cards_per_day)
    cards = []
    for entry in entries:
        preview = srs.preview(entry.card, now)
        cards.append(
            QueueCard(
                word=word(entry.item),
                status=card_status(entry.card),
                intervals=Intervals(
                    again=int(preview[Rating.Again].total_seconds()),
                    hard=int(preview[Rating.Hard].total_seconds()),
                    good=int(preview[Rating.Good].total_seconds()),
                    easy=int(preview[Rating.Easy].total_seconds()),
                ),
            )
        )
    return cards


@router.post("/review/{item_slug}")
async def review(
    item_slug: str, body: ReviewRequest, user: CurrentUser, session: SessionDep
) -> ReviewResult:
    now = datetime.now(UTC)
    try:
        outcome = await service.review(
            session, user.id, item_slug, RATINGS[body.rating], body.duration_ms, now
        )
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Word not found in your decks") from None
    return ReviewResult(
        status=card_status(outcome.card),
        due=outcome.card.due,
        interval_seconds=max(int((outcome.card.due - now).total_seconds()), 0),
    )


@router.get("/review/summary")
async def review_summary(
    user: CurrentUser, session: SessionDep, settings: SettingsDep, tz: TimezoneDep
) -> ReviewSummary:
    s = await service.summary(session, user.id, datetime.now(UTC), tz, settings.new_cards_per_day)
    return ReviewSummary(
        due_now=s.due_now,
        new_available_today=s.new_available_today,
        reviewed_today=s.reviewed_today,
        streak_days=s.streak_days,
        total_cards=s.total_cards,
        mature_cards=s.mature_cards,
    )
