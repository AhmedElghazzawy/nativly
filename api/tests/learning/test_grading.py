# ruff: noqa: RUF001 - look-alike characters are the inputs under test for normalize()
import pytest

from app.learning.grading import (
    ResponseMismatchError,
    grade_cloze,
    grade_mcq,
    grade_reorder,
    normalize,
    update_mastery,
)

MCQ_PAYLOAD = {"prompt": "?", "options": ["a", "b", "c"]}
MCQ_ANSWER = {"correct": 1, "explanation": "b"}
CLOZE_ANSWER = {"blanks": [["didn't", "did not"], ["go"]], "explanation": "x"}
REORDER_PAYLOAD = {"prompt": "?", "tokens": ["home", "I", "walked"]}
REORDER_ANSWER = {"sequence": ["I", "walked", "home"], "explanation": "x"}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Didn’t  ", "didn't"),  # curly apostrophe from a phone keyboard
        ("GO", "go"),
        ("did   not", "did not"),
        ("ｇｏ", "go"),  # full-width letters (NFKC)
    ],
)
def test_normalize(raw: str, expected: str) -> None:
    assert normalize(raw) == expected


def test_mcq_correct_and_wrong() -> None:
    assert grade_mcq(MCQ_ANSWER, MCQ_PAYLOAD, 1).is_correct
    wrong = grade_mcq(MCQ_ANSWER, MCQ_PAYLOAD, 0)
    assert (wrong.is_correct, wrong.score, wrong.correct_answer) == (False, 0.0, 1)


def test_mcq_choice_out_of_range() -> None:
    with pytest.raises(ResponseMismatchError):
        grade_mcq(MCQ_ANSWER, MCQ_PAYLOAD, 3)


def test_cloze_accepts_any_listed_answer_case_and_space_insensitive() -> None:
    result = grade_cloze(CLOZE_ANSWER, ["Did  NOT", " go "])

    assert result.is_correct
    assert result.score == 1.0
    assert result.correct_answer == ["didn't", "go"]


def test_cloze_gives_partial_credit() -> None:
    result = grade_cloze(CLOZE_ANSWER, ["didn't", "went"])

    assert not result.is_correct
    assert result.score == 0.5


def test_cloze_blank_count_must_match() -> None:
    with pytest.raises(ResponseMismatchError, match="expected 2"):
        grade_cloze(CLOZE_ANSWER, ["didn't"])


def test_reorder_exact_sequence_required() -> None:
    assert grade_reorder(REORDER_ANSWER, REORDER_PAYLOAD, ["I", "walked", "home"]).is_correct
    assert not grade_reorder(REORDER_ANSWER, REORDER_PAYLOAD, ["home", "I", "walked"]).is_correct


def test_reorder_rejects_foreign_or_missing_tokens() -> None:
    with pytest.raises(ResponseMismatchError):
        grade_reorder(REORDER_ANSWER, REORDER_PAYLOAD, ["I", "ran", "home"])


def test_mastery_moves_toward_result_and_stays_bounded() -> None:
    assert update_mastery(0.0, 1.0) == pytest.approx(0.3)
    assert update_mastery(0.3, 1.0) == pytest.approx(0.51)
    assert update_mastery(0.51, 0.0) == pytest.approx(0.357)
    mastery = 0.0
    for _ in range(50):
        mastery = update_mastery(mastery, 1.0)
    assert 0.99 < mastery <= 1.0
