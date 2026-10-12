from typing import Any

import pytest
import yaml
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning.importer import ContentError, import_content, load_all
from tests.content import ContentDir, course_yaml

API = "/api/v1"
RIGHT, WRONG = 0, 1  # every test item has option 0 correct


def bank(skill: str, per_level: int = 3) -> dict[str, Any]:
    return {
        "skill": skill,
        "items": [
            {
                "slug": f"t-{skill}-{level.lower()}-{i}",
                "level": level,
                "prompt": f"{skill} {level} question {i}",
                "options": ["right", "wrong", "also wrong"],
                "answer": RIGHT,
                **({"passage": "A short text."} if skill == "reading" else {}),
            }
            for level in ("A1", "A2", "B1", "B2")
            for i in range(per_level)
        ],
    }


def write_bank(content: ContentDir, per_level: int = 3) -> None:
    folder = content.root / "en" / "placement"
    folder.mkdir(parents=True, exist_ok=True)
    for skill in ("grammar", "vocab", "reading"):
        (folder / f"{skill}.yaml").write_text(yaml.safe_dump(bank(skill, per_level)))


@pytest.fixture(autouse=True)
async def placement_bank(session: AsyncSession, content: ContentDir) -> None:
    content.write()  # an A2 course ("en-test")
    content.write(
        course=course_yaml(
            slug="en-test-b1",
            cefr_level="B1",
            objectives=[{"slug": "obj-b1", "skill": "grammar", "can_do": "B1 things."}],
        ),
        units=[],
        course_dir="en/b1",
    )
    write_bank(content)
    await import_content(session, content.root)


async def start(client: AsyncClient, headers: dict[str, str]) -> Any:
    response = await client.post(f"{API}/placement/sessions", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def reply(client: AsyncClient, headers: dict[str, str], state: Any, choice: int) -> Any:
    return await client.post(
        f"{API}/placement/sessions/{state['id']}/answers",
        json={"item_slug": state["question"]["slug"], "choice": choice},
        headers=headers,
    )


async def run(client: AsyncClient, headers: dict[str, str], choose: Any) -> Any:
    state = await start(client, headers)
    asked: list[str] = []
    while state["status"] == "in_progress":
        asked.append(state["question"]["slug"])
        response = await reply(client, headers, state, choose(state["question"]))
        assert response.status_code == 200, response.text
        state = response.json()
    assert len(asked) == len(set(asked)), "an item was asked twice"
    return state


async def test_placement_requires_authentication(client: AsyncClient) -> None:
    assert (await client.post(f"{API}/placement/sessions")).status_code == 401


async def test_starts_with_a_b1_grammar_question_without_the_answer(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    state = await start(client, auth_headers)

    assert state["status"] == "in_progress"
    assert (state["answered"], state["total"]) == (0, 18)
    question = state["question"]
    assert question["skill"] == "grammar"
    assert "B1" in question["prompt"]
    assert "answer" not in question


async def test_starting_again_resumes_the_same_test(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    first = await start(client, auth_headers)

    again = await start(client, auth_headers)

    assert again["id"] == first["id"]
    assert again["question"] == first["question"]


async def test_strong_learner_places_at_the_top(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    result = (await run(client, auth_headers, lambda q: RIGHT))["result"]

    assert result["overall"] == "B2"
    assert {s["level"] for s in result["skills"].values()} == {"B2"}
    # No B2 course exists yet: recommend the highest course below B2.
    assert result["recommended_course"] == "en-test-b1"
    levels = (await client.get(f"{API}/me/levels", headers=auth_headers)).json()
    assert [(lvl["skill"], lvl["level"], lvl["source"]) for lvl in levels] == [
        ("reading", "B2", "placement"),
        ("grammar", "B2", "placement"),
        ("vocab", "B2", "placement"),
    ]


async def test_beginner_places_at_a1(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    result = (await run(client, auth_headers, lambda q: WRONG))["result"]

    assert result["overall"] == "A1"
    assert result["recommended_course"] == "en-test"  # lowest course available


async def test_mixed_skills_use_the_lower_median(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    # Perfect grammar, failing vocab and reading -> overall follows the weaker skills.
    result = (
        await run(client, auth_headers, lambda q: RIGHT if q["skill"] == "grammar" else WRONG)
    )["result"]

    assert result["skills"]["grammar"]["level"] == "B2"
    assert result["skills"]["vocab"]["level"] == "A1"
    assert result["overall"] == "A1"


async def test_answers_must_match_the_current_question(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    state = await start(client, auth_headers)

    wrong_item = await client.post(
        f"{API}/placement/sessions/{state['id']}/answers",
        json={"item_slug": "t-grammar-a1-0", "choice": 0},
        headers=auth_headers,
    )
    out_of_range = await reply(client, auth_headers, state, 7)

    assert wrong_item.status_code == 409
    assert out_of_range.status_code == 422


async def test_finished_tests_accept_no_more_answers(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    done = await run(client, auth_headers, lambda q: RIGHT)

    response = await client.post(
        f"{API}/placement/sessions/{done['id']}/answers",
        json={"item_slug": "t-grammar-b1-0", "choice": 0},
        headers=auth_headers,
    )
    latest = (await client.get(f"{API}/placement/sessions/latest", headers=auth_headers)).json()

    assert response.status_code == 409
    assert latest["status"] == "completed"
    assert latest["question"] is None


async def test_a_learner_cannot_answer_someone_elses_test(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    state = await start(client, auth_headers)
    other = {"email": "other@example.com", "password": "other-password"}
    await client.post(f"{API}/auth/register", json=other)
    token = (await client.post(f"{API}/auth/login", json=other)).json()["access_token"]

    response = await reply(client, {"Authorization": f"Bearer {token}"}, state, RIGHT)

    assert response.status_code == 404


async def test_small_bank_falls_back_to_nearest_levels_and_still_finishes(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: AsyncSession,
    content: ContentDir,
) -> None:
    # Only one B2 item per skill: an all-right run must fall back to B1 items, not crash.
    for skill in ("grammar", "vocab", "reading"):
        b = bank(skill, per_level=3)
        b["items"] = [
            i for i in b["items"] if not (i["level"] == "B2" and not i["slug"].endswith("-0"))
        ]
        (content.root / "en" / "placement" / f"{skill}.yaml").write_text(yaml.safe_dump(b))
    await import_content(session, content.root)

    result = (await run(client, auth_headers, lambda q: RIGHT))["result"]

    assert result["overall"] == "B2"


def test_invalid_placement_item_is_rejected(content: ContentDir) -> None:
    folder = content.root / "en" / "placement"
    folder.mkdir(parents=True, exist_ok=True)
    broken = bank("grammar", per_level=1)
    broken["items"][0]["answer"] = 9
    (folder / "grammar.yaml").write_text(yaml.safe_dump(broken))

    with pytest.raises(ContentError, match="answer index out of range"):
        load_all(content.root)
