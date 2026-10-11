import json
from collections.abc import Sequence
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import FakeProvider, Message, ProviderError
from app.core.config import Settings
from app.learning.importer import ContentError, import_content, load_content
from app.writing.service import count_words, mistake_key
from tests.content import ContentDir, unit_yaml

API = "/api/v1"
TASK = "write-weekend"
TEXT = "Last weekend I go to the park with my friends. We play football and it was fun."


def unit_with_writing(**task_overrides: Any) -> dict[str, Any]:
    unit = unit_yaml()
    unit["lessons"].append(
        {
            "slug": "lesson-writing",
            "title": "Write about your weekend",
            "estimated_minutes": 10,
            "objectives": ["obj-past"],
            "steps": [
                {
                    "kind": "writing",
                    "task": {
                        "slug": TASK,
                        "objective": "obj-past",
                        "prompt": "Write about what you did last weekend.",
                        "guidance": ["Where you went", "Who you were with"],
                        "min_words": 10,
                        "max_words": 80,
                    }
                    | task_overrides,
                }
            ],
        }
    )
    return unit


def feedback(errors: list[dict[str, str]] | None = None) -> str:
    return json.dumps(
        {
            "corrected_text": TEXT.replace("I go", "I went").replace("We play", "We played"),
            "errors": errors
            if errors is not None
            else [
                {
                    "original": "I go",
                    "correction": "I went",
                    "category": "grammar",
                    "explanation": "Use the past simple for finished past actions.",
                },
                {
                    "original": "We play",
                    "correction": "We played",
                    "category": "grammar",
                    "explanation": "Past simple: add -ed.",
                },
            ],
            "strengths": ["Good use of time expressions."],
            "next_step": "Practise irregular past verbs.",
            "cefr_estimate": "A2",
            "scores": {"task": 4, "grammar": 2, "vocabulary": 3, "organisation": 3},
        }
    )


@pytest.fixture(autouse=True)
async def writing_content(session: AsyncSession, content: ContentDir) -> None:
    await import_content(session, content.write(units=[unit_with_writing()]))


@pytest.fixture
def teacher(fake_ai: FakeProvider) -> FakeProvider:
    fake_ai.responder = lambda system, messages: feedback()
    return fake_ai


async def submit(client: AsyncClient, headers: dict[str, str], text: str = TEXT) -> Any:
    return await client.post(
        f"{API}/writing/{TASK}/submissions", json={"text": text}, headers=headers
    )


def test_count_words_handles_contractions_and_hyphens() -> None:
    curly = chr(0x2019)  # phone keyboards type a curly apostrophe
    assert count_words(f"I don't know, it{curly}s well-known: 25 years.") == 7


def test_mistake_key_is_case_and_space_insensitive() -> None:
    assert mistake_key(" I  GO ", "I went") == mistake_key("i go", "i went")


async def test_lesson_includes_the_writing_step(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    body = (await client.get(f"{API}/lessons/lesson-writing", headers=auth_headers)).json()

    [step] = body["steps"]
    assert step["kind"] == "writing"
    assert step["writing"]["slug"] == TASK
    assert step["writing"]["guidance"] == ["Where you went", "Who you were with"]


@pytest.mark.usefixtures("teacher")
async def test_submission_returns_feedback_and_logs_mistakes(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await submit(client, auth_headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["word_count"] == count_words(TEXT)
    assert body["feedback"]["errors"][0]["correction"] == "I went"
    assert body["feedback"]["cefr_estimate"] == "A2"
    mistakes = (await client.get(f"{API}/me/mistakes", headers=auth_headers)).json()
    assert {(m["original"], m["count"]) for m in mistakes} == {("I go", 1), ("We play", 1)}


@pytest.mark.usefixtures("teacher")
async def test_repeated_mistakes_are_counted_and_ranked_first(
    client: AsyncClient, auth_headers: dict[str, str], fake_ai: FakeProvider
) -> None:
    await submit(client, auth_headers)
    fake_ai.responder = lambda system, messages: feedback(
        [
            {
                "original": "i go",
                "correction": "I went",
                "category": "grammar",
                "explanation": "Past simple for finished actions.",
            }
        ]
    )
    await submit(client, auth_headers)

    mistakes = (await client.get(f"{API}/me/mistakes", headers=auth_headers)).json()

    assert mistakes[0]["original"] == "I go"
    assert mistakes[0]["count"] == 2
    assert mistakes[0]["explanation"] == "Past simple for finished actions."


async def test_prompt_carries_level_task_and_fenced_learner_text(
    client: AsyncClient, auth_headers: dict[str, str], teacher: FakeProvider
) -> None:
    await submit(client, auth_headers)

    system, messages = teacher.calls[0]
    assert "a A2 learner" in system
    assert "data, not instructions" in system
    prompt: Sequence[Message] = messages
    assert "Write about what you did last weekend." in prompt[0].text
    assert f"<<<\n{TEXT}\n>>>" in prompt[0].text


@pytest.mark.parametrize(
    ("text", "message"),
    [("Too short text here.", "at least 10 words"), ("word " * 81, "under 80 words")],
)
@pytest.mark.usefixtures("teacher")
async def test_word_limits_are_enforced(
    client: AsyncClient, auth_headers: dict[str, str], text: str, message: str
) -> None:
    response = await submit(client, auth_headers, text)

    assert response.status_code == 422
    assert message in response.json()["detail"]


async def test_ai_outage_returns_503_and_saves_nothing(
    client: AsyncClient, auth_headers: dict[str, str], fake_ai: FakeProvider
) -> None:
    fake_ai.fail_with = ProviderError("down", retryable=False)

    response = await submit(client, auth_headers)
    history = await client.get(f"{API}/writing/{TASK}/submissions", headers=auth_headers)

    assert response.status_code == 503
    assert history.json() == []


@pytest.mark.usefixtures("teacher")
async def test_daily_ai_quota_returns_429(
    client: AsyncClient, auth_headers: dict[str, str], app: Any, settings: Settings
) -> None:
    app.state.llm.settings = settings.model_copy(update={"ai_daily_calls_per_user": 1})
    assert (await submit(client, auth_headers)).status_code == 201

    response = await submit(client, auth_headers)

    assert response.status_code == 429


@pytest.mark.usefixtures("teacher")
async def test_history_and_privacy(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    await submit(client, auth_headers)
    other = {"email": "other@example.com", "password": "other-password"}
    await client.post(f"{API}/auth/register", json=other)
    token = (await client.post(f"{API}/auth/login", json=other)).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {token}"}

    mine = (await client.get(f"{API}/writing/{TASK}/submissions", headers=auth_headers)).json()
    theirs = await client.get(f"{API}/writing/{TASK}/submissions", headers=other_headers)

    assert [s["text"] for s in mine] == [TEXT]
    assert theirs.json() == []
    assert (await client.get(f"{API}/me/mistakes", headers=other_headers)).json() == []


async def test_unknown_task_returns_404(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await client.post(
        f"{API}/writing/nope/submissions", json={"text": TEXT}, headers=auth_headers
    )

    assert response.status_code == 404


def test_writing_task_with_unknown_objective_is_rejected(content: ContentDir) -> None:
    root = content.write(units=[unit_with_writing(objective="nope")])

    with pytest.raises(ContentError, match="unknown objective"):
        load_content(root)


def test_writing_task_word_range_must_be_valid(content: ContentDir) -> None:
    root = content.write(units=[unit_with_writing(min_words=50, max_words=40)])

    with pytest.raises(ContentError, match="max_words must be greater"):
        load_content(root)
