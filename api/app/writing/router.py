from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.ai.llm import LLM, AIQuotaExceededError, AIUnavailableError, get_llm
from app.auth.dependencies import CurrentUser, SessionDep
from app.learning.service import NotFoundError
from app.writing import service
from app.writing.feedback import WritingFeedback
from app.writing.models import WritingSubmission
from app.writing.schemas import MistakeRead, SubmissionRead, SubmissionRequest

router = APIRouter(tags=["writing"])

LLMDep = Annotated[LLM, Depends(get_llm)]


def _read(submission: WritingSubmission, task_slug: str) -> SubmissionRead:
    return SubmissionRead(
        id=submission.id,
        task_slug=task_slug,
        text=submission.text,
        word_count=submission.word_count,
        feedback=WritingFeedback.model_validate(submission.feedback),
        created_at=submission.created_at,
    )


@router.post("/writing/{slug}/submissions", status_code=status.HTTP_201_CREATED)
async def submit(
    slug: str, body: SubmissionRequest, user: CurrentUser, session: SessionDep, llm: LLMDep
) -> SubmissionRead:
    try:
        submission, _ = await service.submit(session, llm, user.id, slug, body.text)
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Writing task not found") from None
    except service.WordCountError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
    except AIQuotaExceededError:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "You've used today's AI feedback. It resets within 24 hours.",
        ) from None
    except AIUnavailableError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Writing feedback is unavailable right now. Please try again later.",
        ) from None
    return _read(submission, slug)


@router.get("/writing/{slug}/submissions")
async def history(slug: str, user: CurrentUser, session: SessionDep) -> list[SubmissionRead]:
    try:
        submissions = await service.list_submissions(session, user.id, slug)
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Writing task not found") from None
    return [_read(s, slug) for s in submissions]


@router.get("/me/mistakes")
async def my_mistakes(
    user: CurrentUser,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[MistakeRead]:
    return [
        MistakeRead(
            category=m.category,
            original=m.original,
            correction=m.correction,
            explanation=m.explanation,
            count=m.count,
            last_seen_at=m.last_seen_at,
        )
        for m in await service.top_mistakes(session, user.id, limit)
    ]
