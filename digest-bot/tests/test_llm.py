"""Feature 004 — AC-001 – AC-006 — LLM abstraction (app/llm/)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# AC-001 / AC-002 — LLMResult, LLMClient Protocol
# ---------------------------------------------------------------------------

def test_llm_result_fields():
    """AC-001: LLMResult carries text, input_tokens, output_tokens, model."""
    from app.llm.base import LLMResult

    result = LLMResult(text="hello", input_tokens=10, output_tokens=20, model="claude-haiku-4-5")

    assert result.text == "hello"
    assert result.input_tokens == 10
    assert result.output_tokens == 20
    assert result.model == "claude-haiku-4-5"


def test_llm_client_is_a_protocol():
    """AC-002: LLMClient is a Protocol with an async complete(prompt, context)."""
    from app.llm.base import LLMClient
    import typing

    assert typing.get_type_hints(LLMClient.complete) is not None
    assert getattr(LLMClient, "_is_protocol", False) is True


# ---------------------------------------------------------------------------
# AC-003 / AC-004 — ClaudeClient
# ---------------------------------------------------------------------------

def _fake_anthropic_response(text="Дайджест готов", input_tokens=100, output_tokens=50):
    response = MagicMock()
    block = MagicMock()
    block.text = text
    response.content = [block]
    response.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    return response


async def test_claude_client_complete_returns_llm_result(monkeypatch):
    """AC-003: complete() calls the Anthropic SDK and maps the response to LLMResult."""
    from app.llm.claude import ClaudeClient

    fake_response = _fake_anthropic_response()
    fake_messages = MagicMock()
    fake_messages.create = AsyncMock(return_value=fake_response)
    fake_async_anthropic = MagicMock()
    fake_async_anthropic.messages = fake_messages

    with patch("app.llm.claude.anthropic.AsyncAnthropic", return_value=fake_async_anthropic):
        client = ClaudeClient(model="claude-haiku-4-5-20251001")
        result = await client.complete(prompt="system prompt", context="post 1\npost 2")

    assert result.text == "Дайджест готов"
    assert result.input_tokens == 100
    assert result.output_tokens == 50
    assert result.model == "claude-haiku-4-5-20251001"
    fake_messages.create.assert_awaited_once()


async def test_claude_client_wraps_sdk_errors(monkeypatch):
    """AC-004: any SDK exception is re-raised as LLMError."""
    from app.llm.claude import ClaudeClient
    from app.llm.base import LLMError

    fake_messages = MagicMock()
    fake_messages.create = AsyncMock(side_effect=RuntimeError("network down"))
    fake_async_anthropic = MagicMock()
    fake_async_anthropic.messages = fake_messages

    with patch("app.llm.claude.anthropic.AsyncAnthropic", return_value=fake_async_anthropic):
        client = ClaudeClient(model="claude-haiku-4-5-20251001")
        with pytest.raises(LLMError):
            await client.complete(prompt="system prompt", context="post 1")


# ---------------------------------------------------------------------------
# AC-005 / AC-006 — get_llm_client() factory
# ---------------------------------------------------------------------------

async def test_get_llm_client_returns_claude_client(monkeypatch):
    """AC-005: LLM_PROVIDER=claude -> ClaudeClient(model=config.LLM_MODEL)."""
    from app.llm import factory
    from app.llm.claude import ClaudeClient

    monkeypatch.setattr(factory.config, "LLM_PROVIDER", "claude")
    monkeypatch.setattr(factory.config, "LLM_MODEL", "claude-haiku-4-5-20251001")

    client = factory.get_llm_client()

    assert isinstance(client, ClaudeClient)
    assert client.model == "claude-haiku-4-5-20251001"


async def test_get_llm_client_unknown_provider_raises(monkeypatch):
    """AC-006: unknown LLM_PROVIDER -> ValueError."""
    from app.llm import factory

    monkeypatch.setattr(factory.config, "LLM_PROVIDER", "openai")

    with pytest.raises(ValueError):
        factory.get_llm_client()
