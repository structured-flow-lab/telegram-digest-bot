"""Feature 005 — AC-120 – AC-125 — format_channel_digest (app/digest/formatter.py)."""

from app.digest.formatter import (
    NOTHING_TO_SUMMARIZE,
    TELEGRAM_MESSAGE_LIMIT,
    ChannelDigestMeta,
    format_channel_digest,
)
from app.digest.summarizer import DigestItem, DigestResult


def _meta(**kwargs):
    defaults = dict(days=7, posts_fetched=10, posts_included=8)
    defaults.update(kwargs)
    return ChannelDigestMeta(**defaults)


def _result(items, prompt_version="digest_v2"):
    return DigestResult(items=items, llm_result=None, prompt_version=prompt_version)


def test_empty_items_returns_nothing_to_summarize_message():
    messages = format_channel_digest("chan_a", _result([]), _meta(posts_included=0))

    assert len(messages) == 1
    assert NOTHING_TO_SUMMARIZE in messages[0]
    assert "@chan_a" in messages[0]
    assert "7 дн." in messages[0]


def test_includes_header_info_and_item_content():
    result = _result(
        [DigestItem(title="Theme A", note="A short note", post_urls=["https://t.me/chan/1"])]
    )

    messages = format_channel_digest("chan_a", result, _meta())

    assert len(messages) == 1
    text = messages[0]
    assert "@chan_a" in text
    assert "10" in text and "8" in text
    assert '<a href="https://t.me/chan/1"><b>Theme A</b></a>' in text
    assert "A short note" in text


def test_item_without_note_has_no_extra_line():
    result = _result([DigestItem(title="Theme A", note="", post_urls=["https://t.me/chan/1"])])

    messages = format_channel_digest("chan_a", result, _meta())

    text = messages[0]
    assert '<a href="https://t.me/chan/1"><b>Theme A</b></a>' in text
    lines = text.strip().splitlines()
    assert lines[-1] == '<a href="https://t.me/chan/1"><b>Theme A</b></a>'


def test_item_with_no_urls_renders_bold_title_without_link():
    result = _result([DigestItem(title="Theme A", note="", post_urls=[])])

    messages = format_channel_digest("chan_a", result, _meta())

    text = messages[0]
    assert "<b>Theme A</b>" in text
    assert "<a href=" not in text


def test_item_with_multiple_urls_renders_extra_numbered_links():
    result = _result(
        [
            DigestItem(
                title="Theme A",
                note="",
                post_urls=["https://t.me/chan/1", "https://t.me/chan/2", "https://t.me/chan/3"],
            )
        ]
    )

    messages = format_channel_digest("chan_a", result, _meta())

    text = messages[0]
    assert '<a href="https://t.me/chan/1"><b>Theme A</b></a>' in text
    assert '<a href="https://t.me/chan/2">2</a>' in text
    assert '<a href="https://t.me/chan/3">3</a>' in text


def test_escapes_html_special_chars_in_item_content():
    result = _result(
        [
            DigestItem(
                title="A & B <test>",
                note="Note with <b>bold</b> & special chars",
                post_urls=["https://t.me/chan/1?a=1&b=2"],
            )
        ]
    )

    messages = format_channel_digest("chan_a", result, _meta())

    text = messages[0]
    assert "<b>A &amp; B &lt;test&gt;</b>" in text
    assert "Note with &lt;b&gt;bold&lt;/b&gt; &amp; special chars" in text
    assert 'href="https://t.me/chan/1?a=1&amp;b=2"' in text


def test_channel_error_returns_single_error_message_with_no_items():
    result = _result([DigestItem(title="Theme A", note="", post_urls=["https://t.me/chan/1"])])
    meta = _meta(posts_fetched=0, posts_included=0, error="boom")

    messages = format_channel_digest("chan_a", result, meta)

    assert len(messages) == 1
    assert "@chan_a" in messages[0]
    assert "boom" in messages[0]
    assert "Theme A" not in messages[0]


def test_splits_into_multiple_messages_when_over_limit():
    big_note = "x" * 3900
    result = _result(
        [
            DigestItem(title="A", note=big_note, post_urls=["https://t.me/chan/1"]),
            DigestItem(title="B", note=big_note, post_urls=["https://t.me/chan/2"]),
        ]
    )

    messages = format_channel_digest("chan_a", result, _meta())

    assert len(messages) == 2
    for m in messages:
        assert len(m) <= TELEGRAM_MESSAGE_LIMIT
    assert "<b>A</b>" in messages[0]
    assert "<b>B</b>" in messages[1]
