"""Format a per-channel DigestResult into Telegram HTML message(s)."""

import html
from dataclasses import dataclass

from app.digest.summarizer import DigestItem, DigestResult

TELEGRAM_MESSAGE_LIMIT = 4096

NOTHING_TO_SUMMARIZE = "За указанный период не нашлось постов для дайджеста."


@dataclass
class ChannelDigestMeta:
    days: int
    posts_fetched: int
    posts_included: int
    error: str | None = None


def _format_header(channel: str, meta: ChannelDigestMeta) -> str:
    return (
        f"📑 <b>@{channel}</b> — дайджест за {meta.days} дн. "
        f"({meta.posts_included} из {meta.posts_fetched} постов)"
    )


def _format_item(item: DigestItem) -> str:
    title = html.escape(item.title)
    urls = [html.escape(url, quote=True) for url in item.post_urls]
    if urls:
        block = f'<a href="{urls[0]}"><b>{title}</b></a>'
    else:
        block = f"<b>{title}</b>"
    if len(urls) > 1:
        extra = ", ".join(f'<a href="{url}">{i}</a>' for i, url in enumerate(urls[1:], start=2))
        block += f" ({extra})"
    if item.note:
        block += f"\n{html.escape(item.note)}"
    return block


def format_channel_digest(
    channel: str, result: DigestResult, meta: ChannelDigestMeta
) -> list[str]:
    header_text = _format_header(channel, meta)

    if meta.error:
        return [f"{header_text}\n\n⚠️ Не удалось прочитать канал: {html.escape(meta.error)}"]

    if not result.items:
        return [f"{header_text}\n\n{NOTHING_TO_SUMMARIZE}"]

    messages: list[str] = []
    current = header_text
    for item in result.items:
        block = _format_item(item)
        candidate = f"{current}\n\n{block}"
        if len(candidate) > TELEGRAM_MESSAGE_LIMIT:
            messages.append(current)
            current = block
        else:
            current = candidate
    messages.append(current)
    return messages
