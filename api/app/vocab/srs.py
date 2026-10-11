"""The only code that talks to the FSRS library. Converts between our rows and fsrs.Card."""

from datetime import datetime, timedelta

from fsrs import Card, Rating, Scheduler, State

from app.vocab.models import CardState, UserCard

DESIRED_RETENTION = 0.9  # aim to recall 90% of cards when they come due

# Fuzzing spreads due dates a little so cards learned together don't all return together.
_scheduler = Scheduler(desired_retention=DESIRED_RETENTION)
# Previews must be stable on screen, so they use the same model without the random fuzz.
_preview = Scheduler(desired_retention=DESIRED_RETENTION, enable_fuzzing=False)


def to_fsrs(row: UserCard | None) -> Card:
    if row is None:
        return Card()
    return Card(
        state=State(row.state),
        step=row.step,
        stability=row.stability,
        difficulty=row.difficulty,
        due=row.due,
        last_review=row.last_review,
    )


def schedule(row: UserCard | None, rating: Rating, now: datetime, duration_ms: int | None) -> Card:
    card, _ = _scheduler.review_card(to_fsrs(row), rating, now, duration_ms)
    return card


def apply(row: UserCard, card: Card, rating: Rating) -> None:
    if rating == Rating.Again and row.state == CardState.REVIEW:
        row.lapses += 1
    row.state = int(card.state)
    row.step = card.step
    row.stability = card.stability
    row.difficulty = card.difficulty
    row.due = card.due
    row.last_review = card.last_review
    row.reps += 1


def preview(row: UserCard | None, now: datetime) -> dict[Rating, timedelta]:
    """How long until the card returns for each possible rating."""
    current = to_fsrs(row)
    return {rating: _preview.review_card(current, rating, now)[0].due - now for rating in Rating}


def retrievability(row: UserCard, now: datetime) -> float:
    """Estimated probability the learner recalls this card right now (0-1)."""
    return float(_scheduler.get_card_retrievability(to_fsrs(row), now))
