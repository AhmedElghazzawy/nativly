import json
from collections.abc import Sequence
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import FakeProvider, Message, ProviderError
from app.auth.models import User
from app.core.config import Settings
from app.learning.models import CefrLevel, Skill
from app.placement.models import SkillLevel

API = "/api/v1"


def turn(
    reply: str = "Oh, you're a nurse? That's a great job. Where do you work?",
    corrections: list[dict[str, str]] | None = None,
    facts: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            "reply": reply,
            "corrections": corrections
            if corrections is not None
            else [
                {
                    "original": "I am nurse",
                    "correction": "I am a nurse",
                    "category": "grammar",
                    "explanation": "Use a/an before jobs.",
                }
            ],
            "new_facts": facts if facts is not None else ["Works as a nurse"],
        }
    )


@pytest.fixture
def teacher(fake_ai: FakeProvider) -> FakeProvider:
    fake_ai.responder = lambda system, messages: turn()
    return fake_ai


async def start(client: AsyncClient, headers: dict[str, str]) -> Any:
    response = await client.post(f"{API}/tutor/sessions", headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def say(client: AsyncClient, headers: dict[str, str], session_id: str, text: str) -> Any:
    return await client.post(
        f"{API}/tutor/sessions/{session_id}/messages", json={"text": text}, headers=headers
    )


async def conversation_detail(client: AsyncClient, headers: dict[str, str], session_id: str) -> Any:
    return await client.get(f"{API}/tutor/sessions/{session_id}", headers=headers)


async def test_tutor_requires_authentication(client: AsyncClient) -> None:
    assert (await client.post(f"{API}/tutor/sessions")).status_code == 401


async def test_first_conversation_opens_with_a_greeting(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    first = await start(client, auth_headers)
    second = await start(client, auth_headers)

    assert [m["speaker"] for m in first["messages"]] == ["tutor"]
    assert "get to know you" in first["messages"][0]["text"]
    assert "Welcome back" in second["messages"][0]["text"]


@pytest.mark.usefixtures("teacher")
async def test_a_turn_returns_the_reply_and_corrects_the_learner(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    conversation = await start(client, auth_headers)

    response = await say(client, auth_headers, conversation["id"], "I am nurse in a hospital.")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tutor"]["text"].startswith("Oh, you're a nurse?")
    assert body["learner"]["corrections"][0]["correction"] == "I am a nurse"
    detail = (
        await client.get(f"{API}/tutor/sessions/{conversation['id']}", headers=auth_headers)
    ).json()
    assert [m["speaker"] for m in detail["messages"]] == ["tutor", "learner", "tutor"]
    assert detail["title"] == "I am nurse in a hospital."


@pytest.mark.usefixtures("teacher")
async def test_corrections_feed_the_mistake_log_and_facts_are_remembered_once(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    conversation = await start(client, auth_headers)
    await say(client, auth_headers, conversation["id"], "I am nurse.")
    await say(client, auth_headers, conversation["id"], "Yes I am nurse.")

    mistakes = (await client.get(f"{API}/me/mistakes", headers=auth_headers)).json()
    facts = (await client.get(f"{API}/me/facts", headers=auth_headers)).json()

    assert [(m["original"], m["count"]) for m in mistakes] == [("I am nurse", 2)]
    assert [f["fact"] for f in facts] == ["Works as a nurse"]


async def test_the_teacher_sees_level_memory_and_recurring_mistakes(
    client: AsyncClient,
    auth_headers: dict[str, str],
    teacher: FakeProvider,
    session: AsyncSession,
) -> None:
    user = await session.scalar(select(User))
    assert user is not None
    session.add(
        SkillLevel(
            user_id=user.id,
            skill=Skill.GRAMMAR,
            cefr_level=CefrLevel.B1,
            score=40,
            source="placement",
        )
    )
    await session.flush()
    conversation = await start(client, auth_headers)
    await say(client, auth_headers, conversation["id"], "I am nurse.")

    await say(client, auth_headers, conversation["id"], "I work at night.")

    system, messages = teacher.calls[-1]
    assert "- Level: B1" in system
    assert "Works as a nurse" in system  # remembered from the previous turn
    assert '"I am nurse" -> "I am a nurse"' in system
    prompt: Sequence[Message] = messages
    assert [m.role for m in prompt] == ["user", "model", "user", "model", "user"]
    assert prompt[-1].text == "I work at night."


async def test_ai_outage_keeps_the_learners_message(
    client: AsyncClient, auth_headers: dict[str, str], fake_ai: FakeProvider
) -> None:
    fake_ai.fail_with = ProviderError("down", retryable=False)
    conversation = await start(client, auth_headers)

    response = await say(client, auth_headers, conversation["id"], "Hello?")
    detail = (
        await client.get(f"{API}/tutor/sessions/{conversation['id']}", headers=auth_headers)
    ).json()

    assert response.status_code == 503
    assert [m["text"] for m in detail["messages"]][-1] == "Hello?"


@pytest.mark.usefixtures("teacher")
async def test_daily_allowance_returns_429(
    client: AsyncClient, auth_headers: dict[str, str], app: Any, settings: Settings
) -> None:
    app.state.llm.settings = settings.model_copy(update={"ai_daily_calls_per_user": 1})
    conversation = await start(client, auth_headers)
    assert (await say(client, auth_headers, conversation["id"], "Hi")).status_code == 200

    assert (await say(client, auth_headers, conversation["id"], "Hi again")).status_code == 429


@pytest.mark.usefixtures("teacher")
async def test_learners_can_see_and_delete_what_the_teacher_remembers(
    client: AsyncClient, auth_headers: dict[str, str], fake_ai: FakeProvider
) -> None:
    conversation = await start(client, auth_headers)
    await say(client, auth_headers, conversation["id"], "I am nurse.")
    fake_ai.responder = lambda system, messages: turn(corrections=[], facts=["Lives in Lisbon"])
    await say(client, auth_headers, conversation["id"], "I live in Lisbon.")
    facts = (await client.get(f"{API}/me/facts", headers=auth_headers)).json()
    assert {f["fact"] for f in facts} == {"Works as a nurse", "Lives in Lisbon"}

    nurse = next(f for f in facts if f["fact"] == "Works as a nurse")
    deleted = await client.delete(f"{API}/me/facts/{nurse['id']}", headers=auth_headers)
    after_one = (await client.get(f"{API}/me/facts", headers=auth_headers)).json()
    cleared = await client.delete(f"{API}/me/facts", headers=auth_headers)
    after_all = (await client.get(f"{API}/me/facts", headers=auth_headers)).json()

    assert deleted.status_code == 204
    assert [f["fact"] for f in after_one] == ["Lives in Lisbon"]
    assert cleared.status_code == 204
    assert after_all == []


@pytest.mark.usefixtures("teacher")
async def test_conversations_and_facts_are_private(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    conversation = await start(client, auth_headers)
    await say(client, auth_headers, conversation["id"], "I am nurse.")
    fact_id = (await client.get(f"{API}/me/facts", headers=auth_headers)).json()[0]["id"]
    other = {"email": "other@example.com", "password": "other-password"}
    await client.post(f"{API}/auth/register", json=other)
    token = (await client.post(f"{API}/auth/login", json=other)).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert (
        await client.get(f"{API}/tutor/sessions/{conversation['id']}", headers=headers)
    ).status_code == 404
    assert (await say(client, headers, conversation["id"], "hi")).status_code == 404
    assert (await client.delete(f"{API}/me/facts/{fact_id}", headers=headers)).status_code == 404
    assert (await client.get(f"{API}/tutor/sessions", headers=headers)).json() == []
