from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning.importer import import_content
from tests.content import ContentDir, unit_yaml

API = "/api/v1"
LESSON = "lesson-1"

CORRECT: dict[str, dict[str, Any]] = {
    "ex-mcq": {"type": "mcq", "choice": 1},
    "ex-cloze": {"type": "cloze", "blanks": ["walked"]},
    "ex-reorder": {"type": "reorder", "sequence": ["I", "walked", "home", "yesterday"]},
}


@pytest.fixture(autouse=True)
async def curriculum(session: AsyncSession, content: ContentDir) -> None:
    await import_content(session, content.write())


async def attempt(
    client: AsyncClient,
    headers: dict[str, str],
    slug: str,
    response: dict[str, Any],
    lesson: str | None = LESSON,
) -> Any:
    body: dict[str, Any] = {"response": response}
    if lesson is not None:
        body["lesson_slug"] = lesson
    return await client.post(f"{API}/exercises/{slug}/attempts", json=body, headers=headers)


async def test_attempt_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        f"{API}/exercises/ex-mcq/attempts", json={"response": CORRECT["ex-mcq"]}
    )

    assert response.status_code == 401


async def test_correct_attempt_reveals_explanation_and_raises_mastery(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await attempt(client, auth_headers, "ex-mcq", CORRECT["ex-mcq"])

    assert response.status_code == 200
    body = response.json()
    assert body["is_correct"] is True
    assert body["score"] == 1.0
    assert body["correct_answer"] == 1
    assert body["explanation"] == "Add -ed."
    assert body["mastery"] == {"objective_slug": "obj-past", "mastery": pytest.approx(0.3)}


async def test_wrong_attempt_shows_correct_answer(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await attempt(client, auth_headers, "ex-cloze", {"type": "cloze", "blanks": ["x"]})

    body = response.json()
    assert body["is_correct"] is False
    assert body["correct_answer"] == ["walked"]
    assert body["mastery"]["mastery"] == 0.0


async def test_mastery_accumulates_across_exercises_of_same_objective(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await attempt(client, auth_headers, "ex-mcq", CORRECT["ex-mcq"])  # obj-past -> 0.3

    response = await attempt(client, auth_headers, "ex-cloze", CORRECT["ex-cloze"])

    assert response.json()["mastery"]["mastery"] == pytest.approx(0.51)


@pytest.mark.parametrize(
    ("slug", "payload", "status"),
    [
        ("ex-mcq", {"type": "cloze", "blanks": ["a"]}, 422),  # wrong response type
        ("ex-mcq", {"type": "mcq", "choice": 9}, 422),  # option out of range
        ("ex-reorder", {"type": "reorder", "sequence": ["a", "b"]}, 422),  # foreign tokens
        ("missing", {"type": "mcq", "choice": 0}, 404),
    ],
)
async def test_invalid_attempts(
    client: AsyncClient,
    auth_headers: dict[str, str],
    slug: str,
    payload: dict[str, Any],
    status: int,
) -> None:
    response = await attempt(client, auth_headers, slug, payload)

    assert response.status_code == status


async def test_attempt_lesson_must_contain_exercise(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    missing = await attempt(client, auth_headers, "ex-mcq", CORRECT["ex-mcq"], lesson="nope")
    assert missing.status_code == 404


async def test_complete_lesson_requires_every_exercise(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await attempt(client, auth_headers, "ex-mcq", CORRECT["ex-mcq"])

    response = await client.post(f"{API}/lessons/{LESSON}/complete", headers=auth_headers)

    assert response.status_code == 409
    assert "2 exercise(s)" in response.json()["detail"]


async def test_lesson_flow_scores_latest_attempts_and_reports_progress(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await attempt(client, auth_headers, "ex-mcq", {"type": "mcq", "choice": 0})  # wrong first
    for slug, response in CORRECT.items():
        await attempt(client, auth_headers, slug, response)

    completed = await client.post(f"{API}/lessons/{LESSON}/complete", headers=auth_headers)
    progress = await client.get(f"{API}/me/progress", headers=auth_headers)

    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["score"] == 1.0  # the retry counts, not the first miss
    body = progress.json()
    assert [(lp["lesson_slug"], lp["status"]) for lp in body["lessons"]] == [(LESSON, "completed")]
    objectives = {o["slug"]: o for o in body["objectives"]}
    assert objectives["obj-past"]["evidence_count"] == 3
    assert objectives["obj-vocab"]["evidence_count"] == 1
    masteries = [o["mastery"] for o in body["objectives"]]
    assert masteries == sorted(masteries)  # weakest first


async def test_progress_is_private_to_each_learner(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await attempt(client, auth_headers, "ex-mcq", CORRECT["ex-mcq"])
    other = {"email": "other@example.com", "password": "other-password"}
    await client.post(f"{API}/auth/register", json=other)
    token = (await client.post(f"{API}/auth/login", json=other)).json()["access_token"]

    response = await client.get(f"{API}/me/progress", headers={"Authorization": f"Bearer {token}"})

    assert response.json() == {"lessons": [], "objectives": []}


@pytest.fixture
async def reading_lesson(session: AsyncSession, content: ContentDir) -> None:
    """Adds lesson-2: an explanation-only lesson that contains no exercises."""
    unit = unit_yaml()
    unit["lessons"].append(
        {
            "slug": "lesson-2",
            "title": "Reading only",
            "estimated_minutes": 5,
            "objectives": ["obj-vocab"],
            "steps": [{"kind": "explain", "body": "Just read this."}],
        }
    )
    await import_content(session, content.write(units=[unit]))


@pytest.mark.usefixtures("reading_lesson")
async def test_attempt_rejects_exercise_from_another_lesson(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await attempt(client, auth_headers, "ex-mcq", CORRECT["ex-mcq"], lesson="lesson-2")

    assert response.status_code == 422
    assert response.json()["detail"] == "Exercise is not part of this lesson"


@pytest.mark.usefixtures("reading_lesson")
async def test_lesson_without_exercises_completes_with_full_score(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(f"{API}/lessons/lesson-2/complete", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["score"] == 1.0


async def test_complete_unknown_lesson_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(f"{API}/lessons/missing/complete", headers=auth_headers)

    assert response.status_code == 404
