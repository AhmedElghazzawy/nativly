from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_CONTENT = Path(__file__).resolve().parents[3] / "content"


def course_yaml(**overrides: Any) -> dict[str, Any]:
    return {
        "slug": "en-test",
        "language": "en",
        "cefr_level": "A2",
        "title": "Test course",
        "objectives": [
            {"slug": "obj-past", "skill": "grammar", "can_do": "Can talk about the past."},
            {"slug": "obj-vocab", "skill": "vocab", "can_do": "Can name time words."},
        ],
    } | overrides


def unit_yaml(**overrides: Any) -> dict[str, Any]:
    return {
        "slug": "unit-1",
        "position": 1,
        "title": "Unit one",
        "lessons": [
            {
                "slug": "lesson-1",
                "title": "Lesson one",
                "estimated_minutes": 10,
                "objectives": ["obj-past"],
                "steps": [
                    {"kind": "explain", "title": "Intro", "body": "Use **-ed**."},
                    {
                        "kind": "exercise",
                        "exercise": {
                            "slug": "ex-mcq",
                            "objective": "obj-past",
                            "type": "mcq",
                            "prompt": "Pick one",
                            "options": ["walk", "walked"],
                            "answer": 1,
                            "explanation": "Add -ed.",
                        },
                    },
                    {
                        "kind": "exercise",
                        "exercise": {
                            "slug": "ex-cloze",
                            "objective": "obj-past",
                            "type": "cloze",
                            "prompt": "Fill in",
                            "text": "I ___ home.",
                            "answers": [["walked"]],
                            "explanation": "Past simple.",
                        },
                    },
                    {
                        "kind": "exercise",
                        "exercise": {
                            "slug": "ex-reorder",
                            "objective": "obj-vocab",
                            "type": "reorder",
                            "prompt": "Order",
                            "answer": ["I", "walked", "home", "yesterday"],
                            "explanation": "Time goes last.",
                        },
                    },
                ],
            }
        ],
    } | overrides


class ContentDir:
    """Writes a content tree like the real `content/` folder into a temp directory."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def write(
        self,
        course: dict[str, Any] | None = None,
        units: list[dict[str, Any]] | None = None,
        course_dir: str = "en/a2",
    ) -> Path:
        base = self.root / course_dir
        (base / "units").mkdir(parents=True, exist_ok=True)
        (base / "course.yaml").write_text(yaml.safe_dump(course or course_yaml()))
        for i, unit in enumerate(units if units is not None else [unit_yaml()], start=1):
            (base / "units" / f"{i:02d}.yaml").write_text(yaml.safe_dump(unit))
        return self.root


@pytest.fixture
def content(tmp_path: Path) -> ContentDir:
    return ContentDir(tmp_path / "content")
