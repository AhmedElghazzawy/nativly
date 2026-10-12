"""The adaptive placement algorithm. Pure functions: no I/O, fully unit-tested.

Each skill is a "staircase": start at B1, move up a level after a right answer and down
after a wrong one, so questions quickly cluster around the learner's real level. After
QUESTIONS_PER_SKILL answers the level is estimated from accuracy per level.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.learning.models import CefrLevel, Skill

LEVELS: tuple[CefrLevel, ...] = (CefrLevel.A1, CefrLevel.A2, CefrLevel.B1, CefrLevel.B2)
START_LEVEL = LEVELS.index(CefrLevel.B1)
SKILLS: tuple[Skill, ...] = (Skill.GRAMMAR, Skill.VOCAB, Skill.READING)
QUESTIONS_PER_SKILL = 6
PASS_RATE = 0.6  # "can do" this level: at least 60% right at it


@dataclass(frozen=True)
class Answer:
    level: CefrLevel
    correct: bool


@dataclass(frozen=True)
class Estimate:
    level: CefrLevel
    score: int  # 0-100: progress towards the next level


def next_level(current: int, correct: bool) -> int:
    """Index into LEVELS of the next question's level."""
    step = 1 if correct else -1
    return min(max(current + step, 0), len(LEVELS) - 1)


def _accuracy(answers: Sequence[Answer], level: CefrLevel) -> float | None:
    at_level = [a.correct for a in answers if a.level == level]
    return sum(at_level) / len(at_level) if at_level else None


def estimate(answers: Sequence[Answer]) -> Estimate:
    """Highest level passed; the score is accuracy one level higher.

    A level is passed when answered at >= PASS_RATE. Levels below the lowest level asked are
    assumed passed: the test started above them and the learner never fell down to them.
    """
    asked = [LEVELS.index(a.level) for a in answers]
    passed = max(min(asked) - 1, 0) if asked else 0  # A1 is the floor of this test
    for index, level in enumerate(LEVELS):
        accuracy = _accuracy(answers, level)
        if accuracy is not None and accuracy >= PASS_RATE:
            passed = index
    level = LEVELS[passed]
    if passed + 1 < len(LEVELS):
        above = _accuracy(answers, LEVELS[passed + 1])
        score = round(100 * above) if above is not None else 0
    else:  # top of the bank: how solidly the top level was passed
        score = round(100 * (_accuracy(answers, level) or 0))
    return Estimate(level=level, score=score)


def overall(levels: Sequence[CefrLevel]) -> CefrLevel:
    """Median skill level, rounding down, so one strong skill doesn't over-place a learner."""
    ranked = sorted(levels, key=lambda lvl: list(CefrLevel).index(lvl))
    return ranked[(len(ranked) - 1) // 2]
