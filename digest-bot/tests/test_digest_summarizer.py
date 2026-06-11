"""Feature 004 — AC-010 – AC-011, AC-040 – AC-043 — summarize (app/digest/summarizer.py)."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.digest.summarizer import PROMPT_PATH, SummarizerError, summarize
from app.llm.base import LLMResult
from app.storage.repositories import CachedPost


def _post(msg_id, text="x" * 50, posted_at=datetime(2026, 1, 1, tzinfo=timezone.utc)):
    return CachedPost(
        telegram_msg_id=msg_id,
        posted_at=posted_at,
        text=text,
        url=f"https://t.me/chan/{msg_id}",
    )


def _llm_returning(text):
    llm = AsyncMock()
    llm.complete.return_value = LLMResult(
        text=text, input_tokens=1, output_tokens=2, model="claude-haiku-4-5"
    )
    return llm


def test_prompt_file_exists_and_mentions_clusters():
    content = PROMPT_PATH.read_text(encoding="utf-8")
    assert "cluster" in content.lower()
    assert "json" in content.lower()


async def test_empty_posts_returns_empty_result_without_calling_llm():
    llm = AsyncMock()

    result = await summarize([], llm)

    assert result.clusters == []
    assert result.llm_result is None
    llm.complete.assert_not_called()


async def test_parses_valid_json_response_into_clusters():
    posts = [_post(1), _post(2), _post(3)]
    response = json.dumps(
        {
            "clusters": [
                {"title": "Theme A", "summary": "Summary A", "post_indices": [0, 2]},
                {"title": "Theme B", "summary": "Summary B", "post_indices": [1]},
            ]
        }
    )
    llm = _llm_returning(response)

    result = await summarize(posts, llm)

    assert len(result.clusters) == 2
    assert result.clusters[0].title == "Theme A"
    assert result.clusters[0].post_urls == ["https://t.me/chan/1", "https://t.me/chan/3"]
    assert result.clusters[1].post_urls == ["https://t.me/chan/2"]
    assert result.llm_result.model == "claude-haiku-4-5"


async def test_parses_json_wrapped_in_markdown_code_fence():
    posts = [_post(1)]
    response = "```json\n" + json.dumps(
        {"clusters": [{"title": "Theme A", "summary": "Summary A", "post_indices": [0]}]}
    ) + "\n```"
    llm = _llm_returning(response)

    result = await summarize(posts, llm)

    assert len(result.clusters) == 1
    assert result.clusters[0].title == "Theme A"


async def test_invalid_json_raises_summarizer_error():
    posts = [_post(1)]
    llm = _llm_returning("not json")

    with pytest.raises(SummarizerError):
        await summarize(posts, llm)


async def test_missing_expected_keys_raises_summarizer_error():
    posts = [_post(1)]
    llm = _llm_returning(json.dumps({"unexpected": []}))

    with pytest.raises(SummarizerError):
        await summarize(posts, llm)
