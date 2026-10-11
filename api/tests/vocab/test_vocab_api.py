from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.learning.importer import ContentError, import_content
from app.vocab.models import Review, UserCard
from tests.content import ContentDir, deck_yaml

API = "/api/v1"
DECK = "deck-1"


@pytest.fixture(autouse=True)
async def vocabulary(session: AsyncSession, content: ContentDir) -> None:
    await import_content(session, content.write(decks=[deck_yaml()]))


async def subscribe(client: AsyncClient, headers: dict[str, str], deck: str = DECK) -> Any:
    return await client.put(f"{API}/decks/{deck}/subscription", headers=headers)


async def queue(client: AsyncClient, headers: dict[str, str], **params: Any) -> Any:
    response = await client.get(f"{API}/review/queue", params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def rate(client: AsyncClient, headers: dict[str, str], slug: str, rating: str) -> Any:
    return await client.post(f"{API}/review/{slug}", json={"rating": rating}, headers=headers)


async def summary(client: AsyncClient, headers: dict[str, str], **params: Any) -> Any:
    response = await client.get(f"{API}/review/summary", params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/decks"),
        ("GET", f"/decks/{DECK}"),
        ("PUT", f"/decks/{DECK}/subscription"),
        ("GET", "/review/queue"),
        ("POST", "/review/w-go"),
        ("GET", "/review/summary"),
    ],
)
async def test_vocabulary_requires_authentication(
    client: AsyncClient, method: str, path: str
) -> None:
    response = await client.request(method, f"{API}{path}", json={"rating": "good"})

    assert response.status_code == 401


async def test_decks_list_shows_size_and_subscription(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    before = (await client.get(f"{API}/decks", headers=auth_headers)).json()
    assert await subscribe(client, auth_headers) is not None
    after = (await client.get(f"{API}/decks", headers=auth_headers)).json()

    assert before == [
        {
            "slug": DECK,
            "title": "Test deck",
            "description": "",
            "cefr_level": "A2",
            "total": 3,
            "studied": 0,
            "subscribed": False,
        }
    ]
    assert after[0]["subscribed"] is True


async def test_subscribe_is_idempotent_and_404s_for_unknown_decks(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    assert (await subscribe(client, auth_headers)).status_code == 204
    assert (await subscribe(client, auth_headers)).status_code == 204
    assert (await subscribe(client, auth_headers, "nope")).status_code == 404


async def test_queue_is_empty_until_a_deck_is_studied(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    assert await queue(client, auth_headers) == []

    await subscribe(client, auth_headers)
    cards = await queue(client, auth_headers)

    assert [c["word"]["slug"] for c in cards] == ["w-go", "w-see", "w-ago"]
    assert {c["status"] for c in cards} == {"new"}
    intervals = cards[0]["intervals"]
    assert intervals["again"] <= intervals["hard"] <= intervals["good"] < intervals["easy"]


async def test_new_words_per_day_are_capped(
    client: AsyncClient, auth_headers: dict[str, str], app: Any, settings: Any
) -> None:
    from app.core.config import get_settings

    app.dependency_overrides[get_settings] = lambda: settings.model_copy(
        update={"new_cards_per_day": 2}
    )
    await subscribe(client, auth_headers)

    assert len(await queue(client, auth_headers)) == 2
    await rate(client, auth_headers, "w-go", "easy")
    await rate(client, auth_headers, "w-see", "easy")

    assert await queue(client, auth_headers) == []  # both introduced today; allowance used
    assert (await summary(client, auth_headers))["new_available_today"] == 0


async def test_reviewing_schedules_the_card(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await subscribe(client, auth_headers)

    easy = (await rate(client, auth_headers, "w-go", "easy")).json()
    good = (await rate(client, auth_headers, "w-see", "good")).json()
    remaining = [c["word"]["slug"] for c in await queue(client, auth_headers)]

    # "Easy" graduates the word to review days away: it leaves today's queue.
    assert easy["status"] == "young"
    assert easy["interval_seconds"] > 24 * 3600
    assert "w-go" not in remaining
    # "Good" on a new word is a short learning step: it returns within this session.
    assert good["status"] == "learning"
    assert 0 < good["interval_seconds"] <= 20 * 60
    assert "w-see" in remaining


async def test_due_cards_come_back_before_new_words(
    client: AsyncClient, auth_headers: dict[str, str], session: AsyncSession
) -> None:
    await subscribe(client, auth_headers)
    await rate(client, auth_headers, "w-ago", "good")
    await session.execute(update(UserCard).values(due=datetime.now(UTC) - timedelta(minutes=1)))

    cards = await queue(client, auth_headers)

    assert cards[0]["word"]["slug"] == "w-ago"
    assert cards[0]["status"] == "learning"
    assert [c["status"] for c in cards[1:]] == ["new", "new"]


async def test_cannot_review_words_outside_studied_decks(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    assert (await rate(client, auth_headers, "w-go", "good")).status_code == 404
    await subscribe(client, auth_headers)
    assert (await rate(client, auth_headers, "missing", "good")).status_code == 404
    assert (await rate(client, auth_headers, "w-go", "perfect")).status_code == 422


async def test_unsubscribing_stops_new_words_but_keeps_due_cards(
    client: AsyncClient, auth_headers: dict[str, str], session: AsyncSession
) -> None:
    await subscribe(client, auth_headers)
    await rate(client, auth_headers, "w-go", "again")
    await session.execute(update(UserCard).values(due=datetime.now(UTC) - timedelta(minutes=1)))

    response = await client.delete(f"{API}/decks/{DECK}/subscription", headers=auth_headers)
    cards = await queue(client, auth_headers)

    assert response.status_code == 204
    assert [c["word"]["slug"] for c in cards] == ["w-go"]


async def test_deck_detail_shows_each_words_status(
    client: AsyncClient, auth_headers: dict[str, str], session: AsyncSession
) -> None:
    await subscribe(client, auth_headers)
    await rate(client, auth_headers, "w-go", "good")
    await rate(client, auth_headers, "w-see", "good")
    await session.execute(
        update(UserCard)
        .where(UserCard.item_id.in_(select(UserCard.item_id).limit(1)))
        .values(state=2, stability=40.0)
    )

    body = (await client.get(f"{API}/decks/{DECK}", headers=auth_headers)).json()

    statuses = {w["slug"]: w["status"] for w in body["words"]}
    assert statuses["w-ago"] == "new"
    assert sorted(statuses.values()) == ["learning", "mature", "new"]
    assert body["studied"] == 2
    assert body["words"][0]["notes"] == "go - went - gone"


async def test_summary_counts_reviews_and_streak(
    client: AsyncClient, auth_headers: dict[str, str], session: AsyncSession
) -> None:
    await subscribe(client, auth_headers)
    await rate(client, auth_headers, "w-go", "good")
    card = await session.scalar(select(UserCard))
    user = await session.scalar(select(User))
    assert card is not None and user is not None
    now = datetime.now(UTC)
    for days_ago in (1, 2, 4):  # a gap on day 3 breaks the streak there
        session.add(
            Review(
                card_id=card.id,
                user_id=user.id,
                rating=3,
                reviewed_at=now - timedelta(days=days_ago),
                due_after=now,
            )
        )
    await session.flush()

    body = await summary(client, auth_headers)

    assert body["reviewed_today"] == 1
    assert body["streak_days"] == 3  # today, yesterday, the day before
    assert body["total_cards"] == 1
    assert body["new_available_today"] == 2


async def test_unknown_timezone_is_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get(
        f"{API}/review/summary", params={"tz": "Mars/Olympus"}, headers=auth_headers
    )

    assert response.status_code == 422


async def test_cards_are_private_to_each_learner(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await subscribe(client, auth_headers)
    await rate(client, auth_headers, "w-go", "good")
    other = {"email": "other@example.com", "password": "other-password"}
    await client.post(f"{API}/auth/register", json=other)
    token = (await client.post(f"{API}/auth/login", json=other)).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert await queue(client, headers) == []
    assert (await summary(client, headers))["total_cards"] == 0


def test_deck_with_unknown_unit_is_rejected(content: ContentDir) -> None:
    from app.learning.importer import load_content

    root = content.write(decks=[deck_yaml(unit="no-such-unit")])

    with pytest.raises(ContentError, match="unknown unit"):
        load_content(root)


def test_word_whose_examples_never_use_it_is_rejected(content: ContentDir) -> None:
    from app.learning.importer import load_content

    deck = deck_yaml()
    deck["items"][2]["examples"] = ["Nothing relevant here."]
    root = content.write(decks=[deck])

    with pytest.raises(ContentError, match="no example uses 'ago'"):
        load_content(root)


async def test_learning_cards_due_soon_return_in_the_same_session(
    client: AsyncClient, auth_headers: dict[str, str], app: Any, settings: Any
) -> None:
    from app.core.config import get_settings

    app.dependency_overrides[get_settings] = lambda: settings.model_copy(
        update={"new_cards_per_day": 1}
    )
    await subscribe(client, auth_headers)
    await rate(client, auth_headers, "w-go", "again")  # due again in about a minute

    cards = await queue(client, auth_headers)

    assert [(c["word"]["slug"], c["status"]) for c in cards] == [("w-go", "learning")]
