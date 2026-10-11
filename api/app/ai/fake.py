"""Demo answers for AI_PROVIDER=fake: local development and e2e tests without an API key.

They are clearly labelled as demo output and never pretend to be real feedback.
"""

import json
import re
from collections.abc import Sequence

from app.ai.providers import FakeProvider, Message, ProviderError

_LEARNER_TEXT = re.compile(r"<<<\n(.*)\n>>>", re.DOTALL)


def _demo_writing_feedback(text: str) -> str:
    return json.dumps(
        {
            "corrected_text": text,
            "errors": [],
            "strengths": ["Demo mode: AI feedback isn't connected, so this text wasn't checked."],
            "next_step": "Connect an AI provider to get real corrections.",
            "cefr_estimate": "A2",
            "scores": {"task": 3, "grammar": 3, "vocabulary": 3, "organisation": 3},
        }
    )


def _respond(system: str, messages: Sequence[Message]) -> str:
    if "marking a learner's short piece of writing" in system:
        match = _LEARNER_TEXT.search(messages[-1].text)
        return _demo_writing_feedback(match.group(1) if match else "")
    raise ProviderError("demo provider has no answer for this request", retryable=False)


def demo_provider() -> FakeProvider:
    return FakeProvider(responder=_respond)
