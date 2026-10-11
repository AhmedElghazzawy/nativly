"""Server-side answer checking. Pure functions: no database, no I/O.

The client never receives answer keys, so it can't grade; it sends the learner's response and
gets the verdict, the correct answer and the explanation back.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.learning.models import ExerciseType

# Curly quotes come from phone keyboards; treat them like straight ones.
_QUOTES = str.maketrans({chr(0x2019): "'", chr(0x2018): "'", chr(0x201C): '"', chr(0x201D): '"'})
_SPACES = re.compile(r"\s+")


@dataclass(frozen=True)
class Grade:
    score: float  # 0.0 to 1.0; partial credit for multi-blank cloze
    is_correct: bool
    correct_answer: Any  # revealed after the attempt, in the same shape as the response


class ResponseMismatchError(ValueError):
    """The response doesn't fit the exercise (wrong blank count, foreign tokens, …)."""


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_QUOTES)
    return _SPACES.sub(" ", text).strip().casefold()


def grade_mcq(answer: dict[str, Any], payload: dict[str, Any], choice: int) -> Grade:
    if not 0 <= choice < len(payload["options"]):
        raise ResponseMismatchError("choice is out of range")
    correct = choice == answer["correct"]
    return Grade(float(correct), correct, answer["correct"])


def grade_cloze(answer: dict[str, Any], blanks: list[str]) -> Grade:
    accepted: list[list[str]] = answer["blanks"]
    if len(blanks) != len(accepted):
        raise ResponseMismatchError(f"expected {len(accepted)} blank(s), got {len(blanks)}")
    hits = [
        normalize(given) in {normalize(option) for option in options}
        for given, options in zip(blanks, accepted, strict=True)
    ]
    score = sum(hits) / len(hits)
    return Grade(score, all(hits), [options[0] for options in accepted])


def grade_reorder(answer: dict[str, Any], payload: dict[str, Any], sequence: list[str]) -> Grade:
    if sorted(sequence) != sorted(payload["tokens"]):
        raise ResponseMismatchError("sequence must use exactly the given tokens")
    correct = sequence == answer["sequence"]
    return Grade(float(correct), correct, answer["sequence"])


def grade(
    exercise_type: ExerciseType,
    payload: dict[str, Any],
    answer: dict[str, Any],
    response: dict[str, Any],
) -> Grade:
    match exercise_type:
        case ExerciseType.MCQ:
            return grade_mcq(answer, payload, response["choice"])
        case ExerciseType.CLOZE:
            return grade_cloze(answer, response["blanks"])
        case ExerciseType.REORDER:
            return grade_reorder(answer, payload, response["sequence"])


# Exponential moving average toward the latest result (build plan §5.2). 0.3 means one
# attempt moves mastery 30% of the way, so a few consistent results dominate an old fluke.
MASTERY_RATE = 0.3


def update_mastery(current: float, score: float, rate: float = MASTERY_RATE) -> float:
    return current + rate * (score - current)
