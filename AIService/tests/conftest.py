import json
from typing import List, Optional

import pytest

from aiservice.errors import AIServiceError
from aiservice.providers.base import Generation, Usage


class FakeProvider:
    """Deterministic stand-in for a provider. Records prompts; returns scripted text or raises."""

    name = "fake"
    model = "fake-model-1"

    def __init__(self, reply=None, *, configured: bool = True, error: Optional[AIServiceError] = None, usage=Usage(11, 7)):
        self.reply = reply
        self.configured = configured
        self.error = error
        self.usage = usage
        self.prompts: List[str] = []

    def is_configured(self) -> bool:
        return self.configured

    async def _answer(self, prompt: str) -> Generation:
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        text = self.reply if isinstance(self.reply, str) else json.dumps(self.reply)
        return Generation(text=text, model=self.model, usage=self.usage)

    async def generate_text(self, *, prompt, system=None, temperature=0.3, max_output_tokens=None):
        return await self._answer(prompt)

    async def generate_json(self, *, prompt, system=None, temperature=0.1):
        return await self._answer(prompt)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def fake():
    return FakeProvider
