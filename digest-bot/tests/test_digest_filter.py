"""Feature 004 — AC-030 – AC-031 — filter_posts (app/digest/filter.py)."""

from datetime import datetime, timezone

from app.digest.filter import filter_posts
from app.storage.repositories import CachedPost

LONG_TEXT_A = "a" * 50
LONG_TEXT_B = "b" * 50
SHORT_TEXT = "too short"


def _post(msg_id, text, posted_at=datetime(2026, 1, 1, tzinfo=timezone.utc)):
    return CachedPost(
        telegram_msg_id=msg_id,
        posted_at=posted_at,
        text=text,
        url=f"https://t.me/channel/{msg_id}",
    )


def test_drops_empty_and_none_text():
    posts = [_post(1, ""), _post(2, None), _post(3, LONG_TEXT_A)]

    result = filter_posts(posts)

    assert [p.telegram_msg_id for p in result] == [3]


def test_drops_short_text():
    posts = [_post(1, SHORT_TEXT), _post(2, LONG_TEXT_A)]

    result = filter_posts(posts)

    assert [p.telegram_msg_id for p in result] == [2]


def test_drops_exact_duplicate_text_keeping_first():
    posts = [_post(1, LONG_TEXT_A), _post(2, LONG_TEXT_B), _post(3, LONG_TEXT_A)]

    result = filter_posts(posts)

    assert [p.telegram_msg_id for p in result] == [1, 2]


def test_keeps_all_when_unique_and_long_enough():
    posts = [_post(1, LONG_TEXT_A), _post(2, LONG_TEXT_B)]

    result = filter_posts(posts)

    assert result == posts
