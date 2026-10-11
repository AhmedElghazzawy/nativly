"""Model providers. Only this module (and app/ai in general) may import a provider SDK."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel

Role = Literal["user", "model"]


@dataclass(frozen=True)
class Message:
    role: Role
    text: str


@dataclass(frozen=True)
class RawCompletion:
    text: str
    model: str
    input_tokens: int | None
    output_tokens: int | None


class ProviderError(Exception):
    """The provider failed (network, quota, server). `retryable` means a retry may succeed."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class LLMProvider(Protocol):
    name: str

    async def generate(
        self,
        *,
        model: str,
        system: str,
        messages: Sequence[Message],
        schema: type[BaseModel] | None,
        temperature: float,
        max_output_tokens: int,
        timeout_seconds: float,
    ) -> RawCompletion: ...


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str) -> None:
        from google import genai  # imported lazily: tests and keyless setups never load it

        self._client = genai.Client(api_key=api_key)

    async def generate(
        self,
        *,
        model: str,
        system: str,
        messages: Sequence[Message],
        schema: type[BaseModel] | None,
        temperature: float,
        max_output_tokens: int,
        timeout_seconds: float,
    ) -> RawCompletion:
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),
        )
        if schema is not None:
            config.response_mime_type = "application/json"
            config.response_json_schema = schema.model_json_schema()
        contents = [types.Content(role=m.role, parts=[types.Part(text=m.text)]) for m in messages]
        try:
            response = await self._client.aio.models.generate_content(
                model=model, contents=contents, config=config
            )
        except errors.ClientError as exc:  # 4xx: bad request, auth, quota (429)
            raise ProviderError(
                f"gemini {exc.code}: {exc.message}", retryable=exc.code == 429
            ) from exc
        except errors.ServerError as exc:  # 5xx
            raise ProviderError(f"gemini {exc.code}: {exc.message}", retryable=True) from exc
        except TimeoutError as exc:
            raise ProviderError("gemini timeout", retryable=True) from exc

        usage = response.usage_metadata
        return RawCompletion(
            text=response.text or "",
            model=model,
            input_tokens=usage.prompt_token_count if usage else None,
            output_tokens=usage.candidates_token_count if usage else None,
        )


Responder = Callable[[str, Sequence[Message]], str]


class FakeProvider:
    """Deterministic provider for tests and local development without an API key."""

    name = "fake"

    def __init__(self, responder: Responder | None = None) -> None:
        self.responder = responder
        self.calls: list[tuple[str, list[Message]]] = []
        self.fail_with: ProviderError | None = None

    async def generate(
        self,
        *,
        model: str,
        system: str,
        messages: Sequence[Message],
        schema: type[BaseModel] | None,
        temperature: float,
        max_output_tokens: int,
        timeout_seconds: float,
    ) -> RawCompletion:
        self.calls.append((system, list(messages)))
        if self.fail_with is not None:
            raise self.fail_with
        if self.responder is None:
            raise ProviderError("FakeProvider has no responder configured", retryable=False)
        text = self.responder(system, messages)
        return RawCompletion(
            text=text, model=model, input_tokens=len(system) // 4, output_tokens=len(text) // 4
        )
