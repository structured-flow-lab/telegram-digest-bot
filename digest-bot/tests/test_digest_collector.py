"""Feature 004 — AC-020 – AC-022 — collect_posts (app/digest/collector.py)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.digest.collector import collect_posts
from app.reader.posts import ChannelFetchError, Post
from app.storage.repositories import CachedPost, Channel

SINCE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _channel(channel_id, username):
    return Channel(id=channel_id, username=username, title=None, added_at="", is_active=1)


def _cached_post(msg_id, posted_at, text="x" * 50, url="https://t.me/c/1"):
    return CachedPost(telegram_msg_id=msg_id, posted_at=posted_at, text=text, url=url)


def _fresh_post(msg_id, posted_at):
    return Post(telegram_msg_id=msg_id, posted_at=posted_at, text="x" * 50, url="https://t.me/c/1")


@pytest.fixture
def client():
    c = AsyncMock()
    c.is_connected = lambda: True
    return c


async def test_fetches_fresh_posts_and_merges_with_cache(client):
    channel = _channel(1, "chan_a")
    cache_repo = AsyncMock()
    cache_repo.latest_cached_at.return_value = None
    cache_repo.get_cached_since.return_value = [
        _cached_post(1, datetime(2026, 1, 2, tzinfo=timezone.utc))
    ]

    with patch(
        "app.digest.collector.fetch_posts",
        AsyncMock(return_value=[_fresh_post(2, datetime(2026, 1, 3, tzinfo=timezone.utc))]),
    ) as mock_fetch:
        result = await collect_posts([channel], SINCE, cache_repo, client)

    mock_fetch.assert_awaited_once()
    cache_repo.upsert_posts.assert_awaited_once()
    assert [p.telegram_msg_id for p in result.posts] == [1]
    assert result.failed_channels == []


async def test_uses_latest_cached_at_as_fetch_start(client):
    channel = _channel(1, "chan_a")
    latest = datetime(2026, 1, 5, tzinfo=timezone.utc)
    cache_repo = AsyncMock()
    cache_repo.latest_cached_at.return_value = latest
    cache_repo.get_cached_since.return_value = []

    with patch(
        "app.digest.collector.fetch_posts", AsyncMock(return_value=[])
    ) as mock_fetch:
        await collect_posts([channel], SINCE, cache_repo, client)

    args, _ = mock_fetch.call_args
    assert args[1] == latest


async def test_channel_fetch_error_is_skipped_not_fatal(client):
    channel_a = _channel(1, "chan_a")
    channel_b = _channel(2, "chan_b")
    cache_repo = AsyncMock()
    cache_repo.latest_cached_at.return_value = None
    cache_repo.get_cached_since.return_value = [
        _cached_post(1, datetime(2026, 1, 2, tzinfo=timezone.utc))
    ]

    async def fetch_side_effect(username, since, limit, client):
        if username == "chan_a":
            raise ChannelFetchError("boom")
        return []

    with patch("app.digest.collector.fetch_posts", side_effect=fetch_side_effect):
        result = await collect_posts([channel_a, channel_b], SINCE, cache_repo, client)

    assert result.failed_channels == ["chan_a"]
    # both channels' cached posts are still included
    assert len(result.posts) == 2


async def test_caps_total_posts_at_max_per_digest(client, monkeypatch):
    monkeypatch.setattr("app.digest.collector.config.MAX_POSTS_PER_DIGEST", 2)
    channel = _channel(1, "chan_a")
    cache_repo = AsyncMock()
    cache_repo.latest_cached_at.return_value = None
    cache_repo.get_cached_since.return_value = [
        _cached_post(1, datetime(2026, 1, 1, tzinfo=timezone.utc)),
        _cached_post(2, datetime(2026, 1, 2, tzinfo=timezone.utc)),
        _cached_post(3, datetime(2026, 1, 3, tzinfo=timezone.utc)),
    ]

    with patch("app.digest.collector.fetch_posts", AsyncMock(return_value=[])):
        result = await collect_posts([channel], SINCE, cache_repo, client)

    assert [p.telegram_msg_id for p in result.posts] == [2, 3]
