"""Call the LLM to cluster + summarise posts into a digest."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.llm.base import LLMClient, LLMResult
from app.storage.repositories import CachedPost

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "digest_v1.md"
PROMPT_VERSION = "digest_v1"

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*\n(.*)\n```\s*$", re.DOTALL)


def _strip_code_fence(text: str) -> str:
    match = _CODE_FENCE_RE.match(text.strip())
    return match.group(1) if match else text


class SummarizerError(Exception):
    """Raised when the LLM response can't be parsed into a digest."""


@dataclass
class DigestCluster:
    title: str
    summary: str
    post_urls: list[str]


@dataclass
class DigestResult:
    clusters: list[DigestCluster]
    llm_result: LLMResult | None


def _build_context(posts: list[CachedPost]) -> str:
    parts = []
    for i, post in enumerate(posts):
        parts.append(f"[{i}] {post.posted_at.isoformat()}\n{post.text}\nURL: {post.url}")
    return "\n\n".join(parts)


async def summarize(posts: list[CachedPost], llm: LLMClient) -> DigestResult:
    if not posts:
        return DigestResult(clusters=[], llm_result=None)

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    context = _build_context(posts)
    result = await llm.complete(prompt=prompt, context=context)

    try:
        data = json.loads(_strip_code_fence(result.text))
        clusters = [
            DigestCluster(
                title=cluster["title"],
                summary=cluster["summary"],
                post_urls=[posts[i].url for i in cluster["post_indices"]],
            )
            for cluster in data["clusters"]
        ]
    except (json.JSONDecodeError, KeyError, TypeError, IndexError) as exc:
        raise SummarizerError(f"Could not parse LLM response: {exc}") from exc

    return DigestResult(clusters=clusters, llm_result=result)
