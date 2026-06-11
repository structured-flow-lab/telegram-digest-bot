"""Feature 003 — AC-010 – AC-024 — channel validation + post fetching (app/reader/posts.py)."""

import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from telethon.errors import UsernameNotOccupiedError, UsernameInvalidError, FloodWaitError
from telethon.tl.types import Channel as TLChannel, Chat as TLChat


@pytest.fixture(autouse=True)
def ensure_config(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake:token")
    monkeypatch.setenv("OWNER_TELEGRAM_ID", "999")
    sys.modules.pop("app.config", None)
    sys.modules.pop("app.reader.posts", None)
    yield
    sys.modules.pop("app.config", None)
    sys.modules.pop("app.reader.posts", None)


def _make_broadcast_channel(username="bbcrussian", title="BBC Russian"):
    entity = MagicMock(spec=TLChannel)
    entity.username = username
    entity.title = title
    entity.broadcast = True
    entity.megagroup = False
    return entity


# ---------------------------------------------------------------------------
# validate_channel (AC-010 – AC-012)
# ---------------------------------------------------------------------------

async def test_validate_channel_returns_channel_info():
    """AC-010."""
    from app.reader.posts import validate_channel, ChannelInfo

    client = MagicMock()
    client.get_entity = AsyncMock(return_value=_make_broadcast_channel())

    info = await validate_channel("bbcrussian", client=client)

    assert info == ChannelInfo(username="bbcrussian", title="BBC Russian", is_public=True)


async def test_validate_channel_not_found_username_not_occupied():
    """AC-011."""
    from app.reader.posts import validate_channel, ChannelNotFound

    client = MagicMock()
    client.get_entity = AsyncMock(side_effect=UsernameNotOccupiedError(MagicMock()))

    with pytest.raises(ChannelNotFound):
        await validate_channel("ghost_channel", client=client)


async def test_validate_channel_not_found_username_invalid():
    """AC-011."""
    from app.reader.posts import validate_channel, ChannelNotFound

    client = MagicMock()
    client.get_entity = AsyncMock(side_effect=UsernameInvalidError(MagicMock()))

    with pytest.raises(ChannelNotFound):
        await validate_channel("!!!invalid", client=client)


async def test_validate_channel_not_public_when_no_username():
    """AC-012: entity without a public username -> ChannelNotPublic."""
    from app.reader.posts import validate_channel, ChannelNotPublic

    entity = _make_broadcast_channel(username=None)
    client = MagicMock()
    client.get_entity = AsyncMock(return_value=entity)

    with pytest.raises(ChannelNotPublic):
        await validate_channel("private_chan", client=client)


async def test_validate_channel_not_public_when_not_broadcast():
    """AC-012: resolved entity is not a broadcast channel -> ChannelNotPublic."""
    from app.reader.posts import validate_channel, ChannelNotPublic

    entity = MagicMock(spec=TLChat)
    entity.username = "some_group"
    entity.title = "Some Group"

    client = MagicMock()
    client.get_entity = AsyncMock(return_value=entity)

    with pytest.raises(ChannelNotPublic):
        await validate_channel("some_group", client=client)


# ---------------------------------------------------------------------------
# fetch_posts (AC-020 – AC-024)
# ---------------------------------------------------------------------------

def _make_message(msg_id, text, date, views=None):
    msg = MagicMock()
    msg.id = msg_id
    msg.message = text
    msg.date = date
    msg.views = views
    return msg


async def test_fetch_posts_returns_posts_oldest_to_newest():
    """AC-020, AC-021: returns Post objects, oldest-to-newest, capped at limit."""
    from app.reader.posts import fetch_posts, Post

    since = datetime(2026, 6, 1, tzinfo=timezone.utc)
    messages = [
        _make_message(3, "third", datetime(2026, 6, 3, tzinfo=timezone.utc), views=30),
        _make_message(2, "second", datetime(2026, 6, 2, tzinfo=timezone.utc), views=20),
        _make_message(1, "first", datetime(2026, 6, 1, 12, tzinfo=timezone.utc), views=10),
    ]

    client = MagicMock()

    async def fake_iter_messages(*args, **kwargs):
        for m in messages:
            yield m

    client.iter_messages = fake_iter_messages

    posts = await fetch_posts("bbcrussian", since=since, limit=100, client=client)

    assert [p.telegram_msg_id for p in posts] == [1, 2, 3]
    assert posts[0] == Post(
        telegram_msg_id=1,
        posted_at=datetime(2026, 6, 1, 12, tzinfo=timezone.utc),
        text="first",
        url="https://t.me/bbcrussian/1",
        views=10,
    )


async def test_fetch_posts_skips_empty_text():
    """AC-022: posts with empty/None .message are skipped."""
    from app.reader.posts import fetch_posts

    since = datetime(2026, 6, 1, tzinfo=timezone.utc)
    messages = [
        _make_message(2, None, datetime(2026, 6, 2, tzinfo=timezone.utc)),
        _make_message(1, "", datetime(2026, 6, 1, 12, tzinfo=timezone.utc)),
        _make_message(3, "has text", datetime(2026, 6, 3, tzinfo=timezone.utc)),
    ]

    client = MagicMock()

    async def fake_iter_messages(*args, **kwargs):
        for m in messages:
            yield m

    client.iter_messages = fake_iter_messages

    posts = await fetch_posts("bbcrussian", since=since, limit=100, client=client)

    assert [p.telegram_msg_id for p in posts] == [3]


async def test_fetch_posts_flood_wait_raises_channel_fetch_error():
    """AC-023: FloodWaitError -> ChannelFetchError, no internal retry/sleep."""
    from app.reader.posts import fetch_posts, ChannelFetchError

    since = datetime(2026, 6, 1, tzinfo=timezone.utc)
    client = MagicMock()

    async def fake_iter_messages(*args, **kwargs):
        raise FloodWaitError(MagicMock())
        yield  # pragma: no cover - make this an async generator

    client.iter_messages = fake_iter_messages

    with pytest.raises(ChannelFetchError):
        await fetch_posts("bbcrussian", since=since, limit=100, client=client)


async def test_fetch_posts_other_error_wrapped():
    """AC-024: any other Telethon/RPC error is wrapped in ChannelFetchError."""
    from app.reader.posts import fetch_posts, ChannelFetchError

    since = datetime(2026, 6, 1, tzinfo=timezone.utc)
    client = MagicMock()

    async def fake_iter_messages(*args, **kwargs):
        raise ConnectionError("boom")
        yield  # pragma: no cover

    client.iter_messages = fake_iter_messages

    with pytest.raises(ChannelFetchError):
        await fetch_posts("bbcrussian", since=since, limit=100, client=client)
