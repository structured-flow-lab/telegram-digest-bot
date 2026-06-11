"""Feature 004 — AC-030 – AC-033 — app/digest/summarizer.py."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest


def _collected_post(msg_id, text, channel_username="channel_a"):
    from app.digest.collector import CollectedPost

    return CollectedPost(
        channel_username=channel_username,
        telegram_msg_id=msg_id,
        posted_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        text=text,
        url=f"https://t.me/{channel_username}/{msg_id}",
    )


def test_prompt_version_and_text_loaded():
    """AC-030: PROMPT_VERSION == 'digest_v1' and PROMPT loaded from digest_v1.md."""
    from app.digest import summarizer

    assert summarizer.PROMPT_VERSION == "digest_v1"
    assert isinstance(summarizer.PROMPT, str)
    assert summarizer.PROMPT.strip() != ""


async def test_summarize_calls_llm_client_with_context(monkeypatch):
    """AC-031: builds a context string from posts and calls llm_client.complete()."""
    from app.digest import summarizer
    from app.llm.base import LLMResult

    posts = [_collected_post(1, "Some post text"), _collected_post(2, "Another post")]

    fake_result = LLMResult(text="summary", input_tokens=10, output_tokens=5, model="claude-haiku-4-5")
    llm_client = AsyncMock()
    llm_client.complete = AsyncMock(return_value=fake_result)

    result = await summarizer.summarize(posts, llm_client)

    assert result is fake_result
    llm_client.complete.assert_awaited_once()
    kwargs = llm_client.complete.await_args.kwargs
    assert kwargs["prompt"] == summarizer.PROMPT
    assert "Some post text" in kwargs["context"]
    assert "Another post" in kwargs["context"]
    assert "channel_a" in kwargs["context"]


async def test_summarize_empty_posts_raises_value_error():
    """AC-032: empty posts -> ValueError."""
    from app.digest import summarizer

    with pytest.raises(ValueError):
        await summarizer.summarize([], AsyncMock())


async def test_summarize_wraps_llm_error_as_digest_error(monkeypatch):
    """AC-033: LLMError from the client -> DigestError."""
    from app.digest import summarizer
    from app.llm.base import LLMError

    llm_client = AsyncMock()
    llm_client.complete = AsyncMock(side_effect=LLMError("rate limited"))

    with pytest.raises(summarizer.DigestError):
        await summarizer.summarize([_collected_post(1, "Some post text")], llm_client)
