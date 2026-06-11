"""Feature 004 — AC-010 – AC-013 — app/digest/filter.py."""

from datetime import datetime, timezone

from app.storage.repositories import CachedPost


def _post(msg_id, text, posted_at=None):
    return CachedPost(
        telegram_msg_id=msg_id,
        posted_at=posted_at or datetime(2026, 6, 1, tzinfo=timezone.utc),
        text=text,
        url=f"https://t.me/channel/{msg_id}",
    )


LONG_TEXT_A = "A" * 120
LONG_TEXT_B = "B" * 120


def test_filter_drops_empty_or_none_text():
    """AC-010: posts with None/empty/whitespace-only text are dropped."""
    from app.digest.filter import filter_posts

    posts = [
        _post(1, None),
        _post(2, ""),
        _post(3, "   "),
        _post(4, LONG_TEXT_A),
    ]

    result = filter_posts(posts)

    assert [p.telegram_msg_id for p in result] == [4]


def test_filter_drops_short_posts():
    """AC-011: posts shorter than MIN_POST_LENGTH (100 chars) are dropped."""
    from app.digest.filter import filter_posts, MIN_POST_LENGTH

    assert MIN_POST_LENGTH == 100

    short_text = "short post"
    posts = [_post(1, short_text), _post(2, LONG_TEXT_A)]

    result = filter_posts(posts)

    assert [p.telegram_msg_id for p in result] == [2]


def test_filter_drops_duplicates_keeping_first():
    """AC-012: exact duplicates (case-insensitive, stripped) -> keep first occurrence."""
    from app.digest.filter import filter_posts

    posts = [
        _post(1, LONG_TEXT_A),
        _post(2, LONG_TEXT_A.lower() + "  "),  # duplicate of #1, different case/whitespace
        _post(3, LONG_TEXT_B),
    ]

    result = filter_posts(posts)

    assert [p.telegram_msg_id for p in result] == [1, 3]


def test_filter_preserves_order():
    """AC-013: relative order of remaining posts is preserved."""
    from app.digest.filter import filter_posts

    posts = [
        _post(3, LONG_TEXT_B),
        _post(1, "too short"),
        _post(2, LONG_TEXT_A),
    ]

    result = filter_posts(posts)

    assert [p.telegram_msg_id for p in result] == [3, 2]
