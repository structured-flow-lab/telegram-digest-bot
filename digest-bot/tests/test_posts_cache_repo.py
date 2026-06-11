"""Feature 003 — AC-030 – AC-032 — PostsCacheRepo (app/storage/repositories.py)."""

from datetime import datetime, timezone

import pytest
import aiosqlite

from app.storage.migrations import run_migrations
from app.storage.repositories import ChannelRepo, PostsCacheRepo
from app.reader.posts import Post


@pytest.fixture
async def conn():
    async with aiosqlite.connect(":memory:") as c:
        c.row_factory = aiosqlite.Row
        await run_migrations(c)
        yield c


@pytest.fixture
async def channel_id(conn):
    repo = ChannelRepo(conn)
    channel = await repo.add("vc_ru", title="VC.ru")
    return channel.id


@pytest.fixture
def repo(conn):
    return PostsCacheRepo(conn)


def _post(msg_id, text, posted_at):
    return Post(
        telegram_msg_id=msg_id,
        posted_at=posted_at,
        text=text,
        url=f"https://t.me/vc_ru/{msg_id}",
        views=None,
    )


async def test_upsert_posts_inserts_and_dedupes(repo, channel_id):
    """AC-030: INSERT OR IGNORE on (channel_id, telegram_msg_id); returns new-row count."""
    posts = [
        _post(1, "first", datetime(2026, 6, 1, tzinfo=timezone.utc)),
        _post(2, "second", datetime(2026, 6, 2, tzinfo=timezone.utc)),
    ]

    inserted = await repo.upsert_posts(channel_id, posts)
    assert inserted == 2

    # Re-inserting the same posts plus one new one only counts the new one.
    more_posts = posts + [_post(3, "third", datetime(2026, 6, 3, tzinfo=timezone.utc))]
    inserted_again = await repo.upsert_posts(channel_id, more_posts)
    assert inserted_again == 1


async def test_latest_cached_at_returns_max_posted_at(repo, channel_id):
    """AC-031."""
    posts = [
        _post(1, "first", datetime(2026, 6, 1, tzinfo=timezone.utc)),
        _post(2, "second", datetime(2026, 6, 5, tzinfo=timezone.utc)),
        _post(3, "third", datetime(2026, 6, 3, tzinfo=timezone.utc)),
    ]
    await repo.upsert_posts(channel_id, posts)

    latest = await repo.latest_cached_at(channel_id)
    assert latest == datetime(2026, 6, 5, tzinfo=timezone.utc)


async def test_latest_cached_at_returns_none_when_empty(repo, channel_id):
    """AC-031."""
    assert await repo.latest_cached_at(channel_id) is None


async def test_get_cached_since_filters_orders_and_caps(repo, channel_id):
    """AC-032: posted_at >= since, oldest-to-newest, capped at limit."""
    posts = [
        _post(1, "too old", datetime(2026, 5, 30, tzinfo=timezone.utc)),
        _post(2, "second", datetime(2026, 6, 2, tzinfo=timezone.utc)),
        _post(3, "first", datetime(2026, 6, 1, tzinfo=timezone.utc)),
        _post(4, "third", datetime(2026, 6, 3, tzinfo=timezone.utc)),
    ]
    await repo.upsert_posts(channel_id, posts)

    since = datetime(2026, 6, 1, tzinfo=timezone.utc)
    cached = await repo.get_cached_since(channel_id, since=since, limit=2)

    assert [c.telegram_msg_id for c in cached] == [3, 2]
