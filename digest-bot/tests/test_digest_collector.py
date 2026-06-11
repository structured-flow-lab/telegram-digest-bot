"""Feature 004 — AC-020 – AC-023 — app/digest/collector.py."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import aiosqlite
import pytest

from app.storage.migrations import run_migrations
from app.storage.repositories import ChannelRepo
from app.reader.posts import ChannelFetchError, Post


@pytest.fixture
async def conn():
    async with aiosqlite.connect(":memory:") as c:
        c.row_factory = aiosqlite.Row
        await run_migrations(c)
        yield c


@pytest.fixture
async def channels(conn):
    repo = ChannelRepo(conn)
    a = await repo.add("channel_a", title="Channel A")
    b = await repo.add("channel_b", title="Channel B")
    return [a, b]


def _post(msg_id, text, posted_at):
    return Post(
        telegram_msg_id=msg_id,
        posted_at=posted_at,
        text=text,
        url=f"https://t.me/x/{msg_id}",
        views=None,
    )


async def test_collect_posts_merges_and_sorts_across_channels(conn, channels, monkeypatch):
    """AC-020 / AC-023: posts from all channels are fetched, cached, and merged sorted by date."""
    from app.digest import collector

    fetched = {
        "channel_a": [_post(1, "a-post", datetime(2026, 6, 1, tzinfo=timezone.utc))],
        "channel_b": [_post(1, "b-post", datetime(2026, 6, 2, tzinfo=timezone.utc))],
    }

    async def fake_fetch_posts(username, since, limit):
        return fetched[username]

    monkeypatch.setattr(collector, "fetch_posts", AsyncMock(side_effect=fake_fetch_posts))

    posts, posts_fetched = await collector.collect_posts(conn, channels, days=7)

    assert posts_fetched == 2
    assert [p.channel_username for p in posts] == ["channel_a", "channel_b"]
    assert [p.posted_at for p in posts] == sorted(p.posted_at for p in posts)


async def test_collect_posts_caps_at_max_per_digest(conn, channels, monkeypatch):
    """AC-021: merged posts capped at MAX_POSTS_PER_DIGEST, keeping the most recent."""
    from app.digest import collector

    many_posts_a = [
        _post(i, f"text {i}", datetime(2026, 6, i, tzinfo=timezone.utc)) for i in range(1, 6)
    ]

    async def fake_fetch_posts(username, since, limit):
        return many_posts_a if username == "channel_a" else []

    monkeypatch.setattr(collector, "fetch_posts", AsyncMock(side_effect=fake_fetch_posts))
    monkeypatch.setattr(collector.config, "MAX_POSTS_PER_DIGEST", 3)

    posts, _ = await collector.collect_posts(conn, channels, days=7)

    assert len(posts) == 3
    # Keeps the most recent posts (6/3, 6/4, 6/5)
    assert [p.posted_at.day for p in posts] == [3, 4, 5]


async def test_collect_posts_skips_channel_on_fetch_error(conn, channels, monkeypatch):
    """AC-022: ChannelFetchError on one channel doesn't fail the whole digest."""
    from app.digest import collector

    async def fake_fetch_posts(username, since, limit):
        if username == "channel_a":
            raise ChannelFetchError("boom")
        return [_post(1, "b-post", datetime(2026, 6, 2, tzinfo=timezone.utc))]

    monkeypatch.setattr(collector, "fetch_posts", AsyncMock(side_effect=fake_fetch_posts))

    posts, posts_fetched = await collector.collect_posts(conn, channels, days=7)

    assert [p.channel_username for p in posts] == ["channel_b"]
    assert posts_fetched == 1
