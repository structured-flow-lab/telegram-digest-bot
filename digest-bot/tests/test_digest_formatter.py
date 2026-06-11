"""Feature 004 — AC-050 – AC-052 — format_digest (app/digest/formatter.py)."""

from app.digest.formatter import (
    NOTHING_TO_SUMMARIZE,
    TELEGRAM_MESSAGE_LIMIT,
    DigestHeader,
    format_digest,
)
from app.digest.summarizer import DigestCluster, DigestResult


def _header(**kwargs):
    defaults = dict(channels=["chan_a", "chan_b"], posts_fetched=10, posts_included=8)
    defaults.update(kwargs)
    return DigestHeader(**defaults)


def test_empty_clusters_returns_nothing_to_summarize_message():
    result = DigestResult(clusters=[], llm_result=None)

    messages = format_digest(result, _header(posts_included=0))

    assert len(messages) == 1
    assert NOTHING_TO_SUMMARIZE in messages[0]
    assert "Дайджест" in messages[0]


def test_includes_header_info_and_cluster_content():
    result = DigestResult(
        clusters=[
            DigestCluster(
                title="Theme A",
                summary="Summary A",
                post_urls=["https://t.me/chan/1", "https://t.me/chan/2"],
            )
        ],
        llm_result=None,
    )

    messages = format_digest(result, _header())

    assert len(messages) == 1
    text = messages[0]
    assert "@chan_a" in text and "@chan_b" in text
    assert "10" in text and "8" in text
    assert "<b>Theme A</b>" in text
    assert "Summary A" in text
    assert '<a href="https://t.me/chan/1">1</a>' in text
    assert '<a href="https://t.me/chan/2">2</a>' in text


def test_failed_channels_are_mentioned():
    result = DigestResult(clusters=[], llm_result=None)

    messages = format_digest(result, _header(posts_included=0, failed_channels=["chan_c"]))

    assert "@chan_c" in messages[0]


def test_splits_into_multiple_messages_when_over_limit():
    big_summary = "x" * 4000
    result = DigestResult(
        clusters=[
            DigestCluster(title="A", summary=big_summary, post_urls=[]),
            DigestCluster(title="B", summary=big_summary, post_urls=[]),
        ],
        llm_result=None,
    )

    messages = format_digest(result, _header())

    assert len(messages) == 2
    for m in messages:
        assert len(m) <= TELEGRAM_MESSAGE_LIMIT
    assert "<b>A</b>" in messages[0]
    assert "<b>B</b>" in messages[1]
