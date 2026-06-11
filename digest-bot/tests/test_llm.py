"""Feature 004 — AC-001 – AC-005 — LLM abstraction (app/llm/)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.base import LLMError, LLMResult
from app.llm.claude import ClaudeClient
from app.llm.factory import get_llm_client


def _make_response(text="hello", input_tokens=10, output_tokens=20, model="claude-haiku-4-5"):
    block = MagicMock()
    block.type = "text"
    block.text = text

    response = MagicMock()
    response.content = [block]
    response.usage.input_tokens = input_tokens
    response.usage.output_tokens = output_tokens
    response.model = model
    return response


@pytest.mark.asyncio
async def test_claude_client_complete_returns_llm_result():
    with patch("app.llm.claude.AsyncAnthropic") as mock_anthropic:
        instance = mock_anthropic.return_value
        instance.messages.create = AsyncMock(return_value=_make_response())

        client = ClaudeClient(model="claude-haiku-4-5")
        result = await client.complete(prompt="system prompt", context="user context")

    assert result == LLMResult(
        text="hello", input_tokens=10, output_tokens=20, model="claude-haiku-4-5"
    )
    instance.messages.create.assert_awaited_once()
    _, kwargs = instance.messages.create.call_args
    assert kwargs["system"] == "system prompt"
    assert kwargs["messages"] == [{"role": "user", "content": "user context"}]


@pytest.mark.asyncio
async def test_claude_client_complete_wraps_sdk_errors():
    with patch("app.llm.claude.AsyncAnthropic") as mock_anthropic:
        instance = mock_anthropic.return_value
        instance.messages.create = AsyncMock(side_effect=RuntimeError("boom"))

        client = ClaudeClient(model="claude-haiku-4-5")

        with pytest.raises(LLMError):
            await client.complete(prompt="p", context="c")


def test_get_llm_client_returns_claude_client(monkeypatch):
    monkeypatch.setattr("app.llm.factory.config.LLM_PROVIDER", "claude")
    monkeypatch.setattr("app.llm.factory.config.LLM_MODEL", "claude-haiku-4-5")

    client = get_llm_client()

    assert isinstance(client, ClaudeClient)
    assert client._model == "claude-haiku-4-5"


def test_get_llm_client_raises_for_unknown_provider(monkeypatch):
    monkeypatch.setattr("app.llm.factory.config.LLM_PROVIDER", "unknown")

    with pytest.raises(ValueError, match="unknown"):
        get_llm_client()
