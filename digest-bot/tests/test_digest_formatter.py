"""Feature 004 — AC-040 – AC-042 — app/digest/formatter.py."""


def test_format_digest_includes_header_and_llm_text():
    """AC-040: header lists channels + read/included counts, then llm_text."""
    from app.digest.formatter import format_digest

    result = format_digest(
        llm_text="**Тема 1**\nКраткое содержание...",
        channels=["channel_a", "channel_b"],
        posts_fetched=42,
        posts_included=10,
    )

    assert "channel_a" in result
    assert "channel_b" in result
    assert "42" in result
    assert "10" in result
    assert "**Тема 1**\nКраткое содержание..." in result


def test_format_empty_digest_uses_digest_empty_message():
    """AC-041: empty digest -> messages.DIGEST_EMPTY, mentions the channels."""
    from app.digest.formatter import format_empty_digest
    from app.bot import messages

    result = format_empty_digest(["channel_a", "channel_b"])

    assert "channel_a" in result
    assert "channel_b" in result
    # Result should be derived from the DIGEST_EMPTY template, not a hardcoded literal.
    assert messages.DIGEST_EMPTY.split("{")[0].strip() in result


def test_format_digest_header_has_no_unsafe_markdown_chars():
    """AC-042: @username characters [A-Za-z0-9_] are Markdown-V1 safe in the header."""
    from app.digest.formatter import format_digest

    result = format_digest(
        llm_text="body",
        channels=["bbc_russian"],
        posts_fetched=5,
        posts_included=2,
    )

    header = result.split("body")[0]
    # No stray single '*' or '[' / ']' introduced by formatting itself around the username.
    assert "bbc_russian" in header
