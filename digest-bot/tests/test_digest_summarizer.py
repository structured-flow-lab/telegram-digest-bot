"""Feature 005 — AC-100 – AC-113 — summarize (app/digest/summarizer.py)."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.digest.summarizer import PROMPTS_DIR, SummarizerError, summarize
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


def test_prompt_file_exists_and_describes_toc_format():
    content = (PROMPTS_DIR / "digest_v2.md").read_text(encoding="utf-8")
    assert "json" in content.lower()
    assert "title" in content.lower()
    assert "post_indices" in content.lower()


async def test_empty_posts_returns_empty_result_without_calling_llm():
    llm = AsyncMock()

    result = await summarize([], llm)

    assert result.items == []
    assert result.llm_result is None
    assert result.prompt_version == "digest_v2"
    llm.complete.assert_not_called()


async def test_parses_valid_json_response_into_items():
    posts = [_post(1), _post(2), _post(3)]
    response = json.dumps(
        {
            "items": [
                {"title": "Theme A", "note": "About A", "post_indices": [0, 2]},
                {"title": "Theme B", "note": "", "post_indices": [1]},
            ]
        }
    )
    llm = _llm_returning(response)

    result = await summarize(posts, llm)

    assert len(result.items) == 2
    assert result.items[0].title == "Theme A"
    assert result.items[0].note == "About A"
    assert result.items[0].post_urls == ["https://t.me/chan/1", "https://t.me/chan/3"]
    assert result.items[1].note == ""
    assert result.items[1].post_urls == ["https://t.me/chan/2"]
    assert result.llm_result.model == "claude-haiku-4-5"
    assert result.prompt_version == "digest_v2"


async def test_parses_json_wrapped_in_markdown_code_fence():
    posts = [_post(1)]
    response = "```json\n" + json.dumps(
        {"items": [{"title": "Theme A", "note": "", "post_indices": [0]}]}
    ) + "\n```"
    llm = _llm_returning(response)

    result = await summarize(posts, llm)

    assert len(result.items) == 1
    assert result.items[0].title == "Theme A"


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


async def test_uses_requested_prompt_version():
    posts = [_post(1)]
    response = json.dumps({"items": [{"title": "Theme A", "note": "", "post_indices": [0]}]})
    llm = _llm_returning(response)

    result = await summarize(posts, llm, prompt_version="digest_v1")

    assert result.prompt_version == "digest_v1"
