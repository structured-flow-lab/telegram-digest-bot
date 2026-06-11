"""Format a DigestResult into Telegram HTML message(s)."""

import html
from dataclasses import dataclass, field

from app.digest.summarizer import DigestCluster, DigestResult

TELEGRAM_MESSAGE_LIMIT = 4096

NOTHING_TO_SUMMARIZE = "За указанный период не нашлось постов для дайджеста."


@dataclass
class DigestHeader:
    channels: list[str]
    posts_fetched: int
    posts_included: int
    failed_channels: list[str] = field(default_factory=list)


def _format_header(header: DigestHeader) -> str:
    channels = ", ".join(f"@{c}" for c in header.channels)
    lines = [
        "📊 <b>Дайджест</b>",
        f"Каналы: {channels}",
        f"Постов прочитано: {header.posts_fetched}",
        f"Постов в дайджесте: {header.posts_included}",
    ]
    if header.failed_channels:
        failed = ", ".join(f"@{c}" for c in header.failed_channels)
        lines.append(f"⚠️ Не удалось прочитать: {failed}")
    return "\n".join(lines)


def _format_cluster(cluster: DigestCluster) -> str:
    title = html.escape(cluster.title)
    summary = html.escape(cluster.summary)
    block = f"<b>{title}</b>\n{summary}"
    if cluster.post_urls:
        links = " ".join(
            f'<a href="{html.escape(url, quote=True)}">{i + 1}</a>'
            for i, url in enumerate(cluster.post_urls)
        )
        block += f"\nИсточники: {links}"
    return block


def format_digest(result: DigestResult, header: DigestHeader) -> list[str]:
    header_text = _format_header(header)

    if not result.clusters:
        return [f"{header_text}\n\n{NOTHING_TO_SUMMARIZE}"]

    messages: list[str] = []
    current = header_text
    for cluster in result.clusters:
        block = _format_cluster(cluster)
        candidate = f"{current}\n\n{block}"
        if len(candidate) > TELEGRAM_MESSAGE_LIMIT:
            messages.append(current)
            current = block
        else:
            current = candidate
    messages.append(current)
    return messages
