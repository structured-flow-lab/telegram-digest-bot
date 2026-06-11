"""LLM abstraction — Protocol + result type shared by all providers."""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


class LLMError(Exception):
    """Raised when an LLM provider call fails for any reason."""


class LLMClient(Protocol):
    async def complete(self, prompt: str, context: str) -> LLMResult: ...
