import uuid
from datetime import UTC, datetime, timedelta

from fsrs import Rating

from app.vocab import srs
from app.vocab.models import CardState, UserCard

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)


def review_card(stability: float, due: datetime) -> UserCard:
    return UserCard(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        item_id=uuid.uuid4(),
        state=int(CardState.REVIEW),
        step=None,
        stability=stability,
        difficulty=5.0,
        due=due,
        last_review=due - timedelta(days=stability),
        reps=5,
        lapses=0,
        created_at=NOW - timedelta(days=60),
    )


def test_new_card_intervals_increase_with_rating() -> None:
    intervals = srs.preview(None, NOW)

    assert (
        intervals[Rating.Again]
        <= intervals[Rating.Hard]
        <= intervals[Rating.Good]
        < intervals[Rating.Easy]
    )
    assert intervals[Rating.Again] < timedelta(minutes=10)  # relearn within the session


def test_good_on_a_mature_card_schedules_further_out_than_its_last_interval() -> None:
    card = review_card(stability=30, due=NOW)

    intervals = srs.preview(card, NOW)

    assert intervals[Rating.Good] > timedelta(days=30)


def test_forgetting_a_review_card_counts_a_lapse_and_relearns() -> None:
    card = review_card(stability=30, due=NOW)

    scheduled = srs.schedule(card, Rating.Again, NOW, duration_ms=4000)
    srs.apply(card, scheduled, Rating.Again)

    assert card.lapses == 1
    assert card.reps == 6
    assert card.state == CardState.RELEARNING
    assert card.due - NOW < timedelta(hours=1)


def test_retrievability_drops_as_time_passes() -> None:
    card = review_card(stability=10, due=NOW + timedelta(days=10))

    fresh = srs.retrievability(card, card.last_review or NOW)
    later = srs.retrievability(card, NOW + timedelta(days=30))

    assert fresh > later
