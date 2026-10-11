from fastapi import APIRouter, HTTPException, status
from pydantic import TypeAdapter

from app.auth.dependencies import CurrentUser, SessionDep
from app.learning import progress, service
from app.learning.grading import ResponseMismatchError
from app.learning.models import CefrLevel, Exercise, Lesson, LessonProgress
from app.learning.schemas import (
    AttemptRequest,
    AttemptResult,
    CourseDetail,
    CourseSummary,
    ExercisePublic,
    LessonDetail,
    LessonProgressRead,
    LessonSummary,
    MasteryRead,
    ObjectiveProgressRead,
    ObjectiveRead,
    ProgressRead,
    StepRead,
    UnitOutline,
)

router = APIRouter(tags=["curriculum"])

_exercise_public: TypeAdapter[ExercisePublic] = TypeAdapter(ExercisePublic)


def _not_found(what: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{what} not found")


def _public_exercise(exercise: Exercise) -> ExercisePublic:
    return _exercise_public.validate_python(
        {"slug": exercise.slug, "type": exercise.type, "difficulty": exercise.difficulty}
        | exercise.payload
    )


def _lesson_summary(lesson: Lesson) -> LessonSummary:
    return LessonSummary(
        slug=lesson.slug,
        position=lesson.position,
        title=lesson.title,
        summary=lesson.summary,
        estimated_minutes=lesson.estimated_minutes,
    )


@router.get("/courses")
async def list_courses(
    _: CurrentUser,
    session: SessionDep,
    language: str | None = None,
    level: CefrLevel | None = None,
) -> list[CourseSummary]:
    courses = await service.list_courses(session, language=language, level=level)
    return [
        CourseSummary(
            slug=c.slug,
            language=c.language,
            cefr_level=c.cefr_level,
            title=c.title,
            description=c.description,
        )
        for c in courses
    ]


@router.get("/courses/{slug}")
async def get_course(slug: str, _: CurrentUser, session: SessionDep) -> CourseDetail:
    try:
        course = await service.get_course(session, slug)
    except service.NotFoundError:
        raise _not_found("Course") from None
    return CourseDetail(
        slug=course.slug,
        language=course.language,
        cefr_level=course.cefr_level,
        title=course.title,
        description=course.description,
        units=[
            UnitOutline(
                slug=u.slug,
                position=u.position,
                title=u.title,
                description=u.description,
                lessons=[_lesson_summary(lesson) for lesson in u.lessons],
            )
            for u in course.units
        ],
    )


@router.get("/lessons/{slug}")
async def get_lesson(slug: str, _: CurrentUser, session: SessionDep) -> LessonDetail:
    try:
        lesson = await service.get_lesson(session, slug)
    except service.NotFoundError:
        raise _not_found("Lesson") from None
    return LessonDetail(
        **_lesson_summary(lesson).model_dump(),
        course_slug=lesson.unit.course.slug,
        unit_slug=lesson.unit.slug,
        objectives=[
            ObjectiveRead(
                slug=o.slug, skill=o.skill, can_do=o.can_do, grammar_point=o.grammar_point
            )
            for o in lesson.objectives
        ],
        steps=[
            StepRead(
                position=s.position,
                kind=s.kind,
                title=s.title,
                body=s.body,
                exercise=_public_exercise(s.exercise) if s.exercise else None,
            )
            for s in lesson.steps
        ],
    )


@router.post("/exercises/{slug}/attempts")
async def submit_attempt(
    slug: str, body: AttemptRequest, user: CurrentUser, session: SessionDep
) -> AttemptResult:
    try:
        outcome = await progress.submit_attempt(session, user.id, slug, body)
    except service.NotFoundError:
        raise _not_found("Exercise or lesson") from None
    except progress.ExerciseNotInLessonError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Exercise is not part of this lesson"
        ) from None
    except ResponseMismatchError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
    return AttemptResult(
        is_correct=outcome.grade.is_correct,
        score=outcome.grade.score,
        correct_answer=outcome.grade.correct_answer,
        explanation=outcome.explanation,
        mastery=MasteryRead(objective_slug=outcome.objective_slug, mastery=outcome.mastery),
    )


def _lesson_progress(row: LessonProgress, lesson: Lesson) -> LessonProgressRead:
    return LessonProgressRead(
        lesson_slug=lesson.slug,
        title=lesson.title,
        status=row.status,
        score=row.score,
        started_at=row.started_at,
        completed_at=row.completed_at,
    )


@router.post("/lessons/{slug}/complete")
async def complete_lesson(slug: str, user: CurrentUser, session: SessionDep) -> LessonProgressRead:
    try:
        row, lesson = await progress.complete_lesson(session, user.id, slug)
    except service.NotFoundError:
        raise _not_found("Lesson") from None
    except progress.LessonIncompleteError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
    return _lesson_progress(row, lesson)


@router.get("/me/progress")
async def my_progress(user: CurrentUser, session: SessionDep) -> ProgressRead:
    lessons, objectives = await progress.get_progress(session, user.id)
    return ProgressRead(
        lessons=[_lesson_progress(row, row.lesson) for row in lessons],
        objectives=[
            ObjectiveProgressRead(
                slug=m.objective.slug,
                skill=m.objective.skill,
                can_do=m.objective.can_do,
                mastery=m.mastery,
                evidence_count=m.evidence_count,
                last_seen_at=m.last_seen_at,
            )
            for m in objectives
        ],
    )
