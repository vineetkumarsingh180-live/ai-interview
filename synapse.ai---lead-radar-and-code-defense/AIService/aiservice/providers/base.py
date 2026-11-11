"""Provider-neutral contract: capabilities talk to `LLMProvider`, never to a vendor SDK."""

import json
from dataclasses import dataclass
from typing import Optional, Protocol, Type, TypeVar

from pydantic import BaseModel, ValidationError

from ..errors import InvalidProviderResponse

M = TypeVar("M", bound=BaseModel)


@dataclass(frozen=True)
class Usage:
    """Token counts exactly as the provider reported them (None when it did not report)."""

    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


@dataclass(frozen=True)
class Generation:
    text: str
    model: str
    usage: Usage = Usage()


class LLMProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def model(self) -> str: ...

    def is_configured(self) -> bool: ...

    async def generate_text(
        self,
        *,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: Optional[int] = None,
    ) -> Generation: ...

    async def generate_json(
        self, *, prompt: str, system: Optional[str] = None, temperature: float = 0.1
    ) -> Generation: ...


def parse_model(generation: Generation, schema: Type[M]) -> M:
    """Validate a JSON generation against a Pydantic model; anything else is InvalidProviderResponse."""
    try:
        data = json.loads(generation.text)
    except (ValueError, TypeError) as exc:
        raise InvalidProviderResponse("The provider did not return valid JSON.") from exc
    if not isinstance(data, dict):
        raise InvalidProviderResponse("The provider returned JSON that is not an object.")
    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        fields = ", ".join(sorted({str(e["loc"][0]) for e in exc.errors() if e["loc"]})) or "unknown"
        raise InvalidProviderResponse(f"The provider's JSON failed validation (fields: {fields}).") from exc
