import pytest

from app.learning.models import CefrLevel
from app.placement.staircase import (
    LEVELS,
    START_LEVEL,
    Answer,
    Estimate,
    estimate,
    next_level,
    overall,
)

A1, A2, B1, B2 = CefrLevel.A1, CefrLevel.A2, CefrLevel.B1, CefrLevel.B2


def test_starts_at_b1_and_moves_one_level_per_answer() -> None:
    assert LEVELS[START_LEVEL] == B1
    assert LEVELS[next_level(START_LEVEL, correct=True)] == B2
    assert LEVELS[next_level(START_LEVEL, correct=False)] == A2


def test_staircase_stays_inside_the_bank() -> None:
    assert next_level(len(LEVELS) - 1, correct=True) == len(LEVELS) - 1
    assert next_level(0, correct=False) == 0


@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        # Strong B2 learner: right at B1, mostly right at B2 (top of the bank).
        (
            [(B1, True), (B2, True), (B2, True), (B2, False), (B1, True), (B2, True)],
            Estimate(B2, 75),
        ),
        # Solid B1, shaky B2: B1 passed, 1 of 3 at B2 -> 33% of the way to B2.
        (
            [(B1, True), (B2, False), (B1, True), (B2, True), (B1, True), (B2, False)],
            Estimate(B1, 33),
        ),
        # A2 learner: fails B1, passes A2.
        (
            [(B1, False), (A2, True), (B1, False), (A2, True), (B1, False), (A2, True)],
            Estimate(A2, 0),
        ),
        # Beginner: wrong everywhere -> the floor of the test.
        (
            [(B1, False), (A2, False), (A1, False), (A1, False), (A1, False), (A1, False)],
            Estimate(A1, 0),
        ),
        # Passed A1, never reached A2 data at >= 60%: A1 with some progress.
        (
            [(B1, False), (A2, False), (A1, True), (A2, True), (B1, False), (A2, False)],
            Estimate(A1, 33),
        ),
    ],
)
def test_estimate(answers: list[tuple[CefrLevel, bool]], expected: Estimate) -> None:
    assert estimate([Answer(level, correct) for level, correct in answers]) == expected


def test_levels_below_the_lowest_question_count_as_passed() -> None:
    # Never asked A1/A2 (started at B1, never fell that far) -> they're assumed passed.
    # 50% at B1 and at B2 passes neither, so A2 with half the way to B1.
    answers = [Answer(B1, True), Answer(B2, True), Answer(B2, False), Answer(B1, False)]

    assert estimate(answers) == Estimate(A2, 50)


def test_overall_is_the_lower_median() -> None:
    assert overall([B1, A2, B2]) == B1
    assert overall([A2, B1]) == A2
    assert overall([B2, B2, A1]) == B2
