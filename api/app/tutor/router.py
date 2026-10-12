import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.ai.llm import LLM, AIQuotaExceededError, AIUnavailableError, get_llm
from app.auth.dependencies import CurrentUser, SessionDep
from app.learning.service import NotFoundError
from app.tutor import service
from app.tutor.models import Speaker, TutorMessage, TutorSession
from app.tutor.prompt import Correction

router = APIRouter(tags=["tutor"])

LLMDep = Annotated[LLM, Depends(get_llm)]


class MessageRead(BaseModel):
    id: uuid.UUID
    speaker: Speaker
    text: str
    corrections: list[Correction]
    created_at: datetime


class SessionSummary(BaseModel):
    id: uuid.UUID
    title: str | None
    message_count: int
    started_at: datetime
    last_message_at: datetime | None


class SessionDetail(SessionSummary):
    messages: list[MessageRead]


class SendRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class TurnRead(BaseModel):
    learner: MessageRead
    tutor: MessageRead


class FactRead(BaseModel):
    id: uuid.UUID
    fact: str
    created_at: datetime


def _message(m: TutorMessage) -> MessageRead:
    return MessageRead(
        id=m.id,
        speaker=m.speaker,
        text=m.text,
        corrections=[Correction.model_validate(c) for c in m.corrections],
        created_at=m.created_at,
    )


def _summary(s: TutorSession) -> SessionSummary:
    return SessionSummary(
        id=s.id,
        title=s.title,
        message_count=s.message_count,
        started_at=s.started_at,
        last_message_at=s.last_message_at,
    )


async def _detail(session: SessionDep, conversation: TutorSession) -> SessionDetail:
    return SessionDetail(
        **_summary(conversation).model_dump(),
        messages=[_message(m) for m in await service.messages(session, conversation.id)],
    )


@router.post("/tutor/sessions", status_code=status.HTTP_201_CREATED)
async def start(user: CurrentUser, session: SessionDep) -> SessionDetail:
    return await _detail(session, await service.start(session, user.id))


@router.get("/tutor/sessions")
async def list_sessions(user: CurrentUser, session: SessionDep) -> list[SessionSummary]:
    return [_summary(s) for s in await service.list_sessions(session, user.id)]


@router.get("/tutor/sessions/{session_id}")
async def get_session(
    session_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> SessionDetail:
    try:
        conversation = await service.get_owned(session, user.id, session_id)
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found") from None
    return await _detail(session, conversation)


@router.post("/tutor/sessions/{session_id}/messages")
async def send(
    session_id: uuid.UUID, body: SendRequest, user: CurrentUser, session: SessionDep, llm: LLMDep
) -> TurnRead:
    try:
        learner, tutor = await service.send(session, llm, user.id, session_id, body.text.strip())
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found") from None
    except AIQuotaExceededError:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "You've reached today's limit for your teacher. It resets within 24 hours.",
        ) from None
    except AIUnavailableError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Your teacher can't answer right now. Your message is saved; try again soon.",
        ) from None
    return TurnRead(learner=_message(learner), tutor=_message(tutor))


@router.get("/me/facts")
async def my_facts(user: CurrentUser, session: SessionDep) -> list[FactRead]:
    """What the teacher remembers about the learner."""
    return [
        FactRead(id=f.id, fact=f.fact, created_at=f.created_at)
        for f in await service.list_facts(session, user.id)
    ]


@router.delete("/me/facts/{fact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def forget_fact(fact_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    try:
        await service.forget_fact(session, user.id, fact_id)
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fact not found") from None


@router.delete("/me/facts", status_code=status.HTTP_204_NO_CONTENT)
async def forget_everything(user: CurrentUser, session: SessionDep) -> None:
    await service.forget_everything(session, user.id)
