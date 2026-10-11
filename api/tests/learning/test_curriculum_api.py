import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning.importer import import_content
from tests.content import ContentDir, course_yaml

API = "/api/v1"


@pytest.fixture
async def curriculum(session: AsyncSession, content: ContentDir) -> None:
    content.write()
    b1_objectives = [{"slug": "obj-b1", "skill": "grammar", "can_do": "Can do B1 things."}]
    content.write(
        course=course_yaml(slug="en-b1", cefr_level="B1", objectives=b1_objectives),
        units=[],
        course_dir="en/b1",
    )
    await import_content(session, content.root)


@pytest.mark.parametrize("path", ["/courses", "/courses/en-test", "/lessons/lesson-1"])
async def test_curriculum_requires_authentication(client: AsyncClient, path: str) -> None:
    response = await client.get(f"{API}{path}")

    assert response.status_code == 401


@pytest.mark.usefixtures("curriculum")
async def test_list_courses(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await client.get(f"{API}/courses", headers=auth_headers)

    assert response.status_code == 200
    assert [c["slug"] for c in response.json()] == ["en-test", "en-b1"]


@pytest.mark.usefixtures("curriculum")
async def test_list_courses_filters_by_level(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get(f"{API}/courses", params={"level": "B1"}, headers=auth_headers)

    assert [c["slug"] for c in response.json()] == ["en-b1"]


@pytest.mark.usefixtures("curriculum")
async def test_course_detail_has_ordered_outline(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get(f"{API}/courses/en-test", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["cefr_level"] == "A2"
    assert [u["slug"] for u in body["units"]] == ["unit-1"]
    assert [lesson["slug"] for lesson in body["units"][0]["lessons"]] == ["lesson-1"]


@pytest.mark.usefixtures("curriculum")
async def test_lesson_detail_never_exposes_answers(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get(f"{API}/lessons/lesson-1", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["course_slug"] == "en-test"
    assert [s["position"] for s in body["steps"]] == [1, 2, 3, 4]
    explain, mcq, cloze, reorder = body["steps"]
    assert explain["exercise"] is None and explain["body"] == "Use **-ed**."
    assert mcq["exercise"]["options"] == ["walk", "walked"]
    assert cloze["exercise"]["blanks"] == 1
    assert sorted(reorder["exercise"]["tokens"]) == sorted(["I", "walked", "home", "yesterday"])
    for step in (mcq, cloze, reorder):
        exercise = step["exercise"]
        assert not {"answer", "answers", "correct", "sequence", "explanation"} & exercise.keys()


@pytest.mark.usefixtures("curriculum")
@pytest.mark.parametrize("path", ["/courses/missing", "/lessons/missing"])
async def test_unknown_slugs_return_404(
    client: AsyncClient, auth_headers: dict[str, str], path: str
) -> None:
    response = await client.get(f"{API}{path}", headers=auth_headers)

    assert response.status_code == 404
