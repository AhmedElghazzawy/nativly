import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.auth.dependencies import CurrentUser, SessionDep
from app.learning.models import CefrLevel, Skill
from app.learning.service import NotFoundError
from app.placement import service
from app.placement.models import PlacementSession

router = APIRouter(tags=["placement"])


class PlacementQuestion(BaseModel):
    slug: str
    skill: Skill
    passage: str | None
    prompt: str
    options: list[str]


class SkillResult(BaseModel):
    level: CefrLevel
    score: int


class PlacementResult(BaseModel):
    skills: dict[Skill, SkillResult]
    overall: CefrLevel | None
    recommended_course: str | None


class PlacementState(BaseModel):
    id: uuid.UUID
    status: Literal["in_progress", "completed"]
    answered: int
    total: int
    question: PlacementQuestion | None
    result: PlacementResult | None


class AnswerRequest(BaseModel):
    item_slug: str = Field(max_length=100)
    choice: int = Field(ge=0)
    duration_ms: int | None = Field(default=None, ge=0, le=3_600_000)


class SkillLevelRead(BaseModel):
    skill: Skill
    level: CefrLevel
    score: int
    source: str


async def _state(session: SessionDep, test: PlacementSession) -> PlacementState:
    item = await service.pending_item(session, test)
    answered, total = service.progress(test)
    return PlacementState(
        id=test.id,
        status=test.status.value,
        answered=min(answered, total),
        total=total,
        question=PlacementQuestion(
            slug=item.slug,
            skill=item.skill,
            passage=item.passage,
            prompt=item.prompt,
            options=item.options,
        )
        if item
        else None,
        result=PlacementResult.model_validate(test.result) if test.result else None,
    )


@router.post("/placement/sessions")
async def start(
    user: CurrentUser,
    session: SessionDep,
    language: Annotated[str, Query(pattern=r"^[a-z]{2}$")] = "en",
) -> PlacementState:
    """Start a placement test, or resume the learner's unfinished one."""
    return await _state(session, await service.start(session, user.id, language))


@router.get("/placement/sessions/latest")
async def latest(user: CurrentUser, session: SessionDep) -> PlacementState:
    test = await service.current_session(session, user.id)
    if test is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No placement test yet")
    return await _state(session, test)


@router.post("/placement/sessions/{session_id}/answers")
async def answer(
    session_id: uuid.UUID, body: AnswerRequest, user: CurrentUser, session: SessionDep
) -> PlacementState:
    try:
        test = await service.answer(
            session, user.id, session_id, body.item_slug, body.choice, body.duration_ms
        )
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Placement test not found") from None
    except service.SessionClosedError:
        raise HTTPException(status.HTTP_409_CONFLICT, "This test is already finished") from None
    except service.WrongItemError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "That isn't the current question; reload the test"
        ) from None
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
    return await _state(session, test)


@router.get("/me/levels")
async def my_levels(user: CurrentUser, session: SessionDep) -> list[SkillLevelRead]:
    return [
        SkillLevelRead(skill=s.skill, level=s.cefr_level, score=s.score, source=s.source)
        for s in await service.skill_levels(session, user.id)
    ]
