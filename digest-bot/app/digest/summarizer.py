"""Call the LLM to build a table-of-contents digest from posts."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.llm.base import LLMClient, LLMResult
from app.storage.repositories import CachedPost

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
DEFAULT_PROMPT_VERSION = "digest_v2"

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*\n(.*)\n```\s*$", re.DOTALL)


def _strip_code_fence(text: str) -> str:
    match = _CODE_FENCE_RE.match(text.strip())
    return match.group(1) if match else text


class SummarizerError(Exception):
    """Raised when the LLM response can't be parsed into a digest."""


@dataclass
class DigestItem:
    title: str
    note: str
    post_urls: list[str]


@dataclass
class DigestResult:
    items: list[DigestItem]
    llm_result: LLMResult | None
    prompt_version: str


def _build_context(posts: list[CachedPost]) -> str:
    parts = []
    for i, post in enumerate(posts):
        parts.append(f"[{i}] {post.posted_at.isoformat()}\n{post.text}\nURL: {post.url}")
    return "\n\n".join(parts)


async def summarize(
    posts: list[CachedPost],
    llm: LLMClient,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
) -> DigestResult:
    if not posts:
        return DigestResult(items=[], llm_result=None, prompt_version=prompt_version)

    prompt_path = PROMPTS_DIR / f"{prompt_version}.md"
    prompt = prompt_path.read_text(encoding="utf-8")
    context = _build_context(posts)
    result = await llm.complete(prompt=prompt, context=context)

    try:
        data = json.loads(_strip_code_fence(result.text))
        items = [
            DigestItem(
                title=item["title"],
                note=item["note"],
                post_urls=[posts[i].url for i in item["post_indices"]],
            )
            for item in data["items"]
        ]
    except (json.JSONDecodeError, KeyError, TypeError, IndexError) as exc:
        raise SummarizerError(f"Could not parse LLM response: {exc}") from exc

    return DigestResult(items=items, llm_result=result, prompt_version=prompt_version)
