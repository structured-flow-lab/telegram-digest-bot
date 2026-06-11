"""Claude implementation of LLMClient via the Anthropic SDK."""

from anthropic import AsyncAnthropic

from app import config
from app.llm.base import LLMError, LLMResult

MAX_TOKENS = 4096


class ClaudeClient:
    def __init__(self, model: str) -> None:
        self._model = model
        self._client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)

    async def complete(self, prompt: str, context: str) -> LLMResult:
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=MAX_TOKENS,
                system=prompt,
                messages=[{"role": "user", "content": context}],
            )
        except Exception as exc:
            raise LLMError(f"Claude API call failed: {exc}") from exc

        text = "".join(
            block.text for block in response.content if block.type == "text"
        )
        return LLMResult(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=response.model,
        )
