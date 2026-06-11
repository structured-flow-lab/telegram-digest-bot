"""Feature 002 — AC-010 – AC-019 — /add /remove /channels handlers.

Feature 003 — AC-040 – AC-043 — wiring `validate_channel()` into /add.
"""

import sys
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
import pytest

from app.storage.migrations import run_migrations


def _make_update(text: str, args: list[str], user_id: int = 999):
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.message = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


def _make_context(args: list[str]):
    context = MagicMock()
    context.args = args
    return context


def _reset_handlers_module():
    """Drop cached `app.config` / `app.bot.handlers` so the next import is fresh.

    Popping from sys.modules alone is not enough: `app.bot` keeps a `handlers`
    attribute pointing at the old module object, so `from app.bot import handlers`
    would silently resolve to the stale module via attribute lookup while
    `unittest.mock.patch("app.bot.handlers...")` re-imports a *different* fresh
    module object — leaving the two out of sync.
    """
    import app
    import app.bot as appbot

    sys.modules.pop("app.config", None)
    sys.modules.pop("app.bot.handlers", None)
    if hasattr(app, "config"):
        delattr(app, "config")
    if hasattr(appbot, "handlers"):
        delattr(appbot, "handlers")


@pytest.fixture(autouse=True)
def ensure_config(monkeypatch):
    """Minimal valid env so app.config / app.bot.handlers import cleanly."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake:token")
    monkeypatch.setenv("OWNER_TELEGRAM_ID", "999")
    _reset_handlers_module()
    yield
    _reset_handlers_module()


@pytest.fixture
async def conn():
    async with aiosqlite.connect(":memory:") as c:
        c.row_factory = aiosqlite.Row
        await run_migrations(c)
        yield c


@pytest.fixture
def handlers(conn, monkeypatch):
    from app.bot import handlers as h
    from app.reader.posts import ChannelInfo

    @asynccontextmanager
    async def fake_get_connection():
        yield conn

    monkeypatch.setattr(h.db, "get_connection", fake_get_connection)

    async def default_validate_channel(username):
        return ChannelInfo(username=username, title=username, is_public=True)

    monkeypatch.setattr(h, "validate_channel", default_validate_channel)
    return h


# ---------------------------------------------------------------------------
# /add
# ---------------------------------------------------------------------------

async def test_add_valid_channel(handlers):
    """AC-010: valid new username is added and confirmed."""
    update = _make_update("/add @bbcrussian", ["@bbcrussian"])
    context = _make_context(["@bbcrussian"])

    await handlers.add_handler(update, context)

    update.message.reply_text.assert_awaited_once()
    msg = update.message.reply_text.await_args.args[0]
    assert "bbcrussian" in msg


async def test_add_no_argument(handlers):
    """AC-011: missing argument -> CHANNEL_INVALID_FORMAT."""
    update = _make_update("/add", [])
    context = _make_context([])

    await handlers.add_handler(update, context)

    update.message.reply_text.assert_awaited_once_with(handlers.messages.CHANNEL_INVALID_FORMAT)


async def test_add_malformed_username(handlers):
    """AC-011: malformed username -> CHANNEL_INVALID_FORMAT."""
    update = _make_update("/add @a", ["@a"])
    context = _make_context(["@a"])

    await handlers.add_handler(update, context)

    update.message.reply_text.assert_awaited_once_with(handlers.messages.CHANNEL_INVALID_FORMAT)


async def test_add_duplicate_channel(handlers):
    """AC-012: already-added channel -> CHANNEL_ALREADY_EXISTS."""
    update1 = _make_update("/add @bbcrussian", ["@bbcrussian"])
    await handlers.add_handler(update1, _make_context(["@bbcrussian"]))

    update2 = _make_update("/add @bbcrussian", ["@bbcrussian"])
    await handlers.add_handler(update2, _make_context(["@bbcrussian"]))

    update2.message.reply_text.assert_awaited_once_with(
        handlers.messages.CHANNEL_ALREADY_EXISTS.format(username="bbcrussian")
    )


async def test_add_channel_limit_reached(handlers, monkeypatch):
    """AC-013: limit reached -> CHANNEL_LIMIT_REACHED."""
    from app.storage import repositories

    monkeypatch.setattr(repositories.config, "MAX_CHANNELS", 1)
    monkeypatch.setattr(handlers.config, "MAX_CHANNELS", 1)

    update1 = _make_update("/add @first_channel", ["@first_channel"])
    await handlers.add_handler(update1, _make_context(["@first_channel"]))

    update2 = _make_update("/add @second_channel", ["@second_channel"])
    await handlers.add_handler(update2, _make_context(["@second_channel"]))

    update2.message.reply_text.assert_awaited_once_with(
        handlers.messages.CHANNEL_LIMIT_REACHED.format(limit=1)
    )


# ---------------------------------------------------------------------------
# /remove
# ---------------------------------------------------------------------------

async def test_remove_existing_channel(handlers):
    """AC-014: existing channel is removed and confirmed."""
    update1 = _make_update("/add @bbcrussian", ["@bbcrussian"])
    await handlers.add_handler(update1, _make_context(["@bbcrussian"]))

    update2 = _make_update("/remove @bbcrussian", ["@bbcrussian"])
    await handlers.remove_handler(update2, _make_context(["@bbcrussian"]))

    update2.message.reply_text.assert_awaited_once_with(
        handlers.messages.CHANNEL_REMOVED.format(username="bbcrussian")
    )


async def test_remove_missing_channel(handlers):
    """AC-015: channel not in the list -> CHANNEL_NOT_FOUND."""
    update = _make_update("/remove @ghost", ["@ghost"])
    await handlers.remove_handler(update, _make_context(["@ghost"]))

    update.message.reply_text.assert_awaited_once_with(
        handlers.messages.CHANNEL_NOT_FOUND.format(username="ghost")
    )


# ---------------------------------------------------------------------------
# /channels
# ---------------------------------------------------------------------------

async def test_channels_empty(handlers):
    """AC-016: zero channels -> CHANNELS_EMPTY."""
    update = _make_update("/channels", [])
    await handlers.channels_handler(update, _make_context([]))

    update.message.reply_text.assert_awaited_once_with(handlers.messages.CHANNELS_EMPTY)


async def test_channels_list(handlers):
    """AC-017: lists one @username per line, prefixed by CHANNELS_HEADER."""
    update1 = _make_update("/add @bbcrussian", ["@bbcrussian"])
    await handlers.add_handler(update1, _make_context(["@bbcrussian"]))

    update2 = _make_update("/add @techcrunch", ["@techcrunch"])
    await handlers.add_handler(update2, _make_context(["@techcrunch"]))

    update3 = _make_update("/channels", [])
    await handlers.channels_handler(update3, _make_context([]))

    msg = update3.message.reply_text.await_args.args[0]
    assert msg.startswith(handlers.messages.CHANNELS_HEADER)
    assert "@bbcrussian" in msg
    assert "@techcrunch" in msg


# ---------------------------------------------------------------------------
# Owner guard (AC-018)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("handler_name,args", [
    ("add_handler", ["@bbcrussian"]),
    ("remove_handler", ["@bbcrussian"]),
    ("channels_handler", []),
])
async def test_handlers_respect_owner_guard(handlers, handler_name, args):
    """AC-018: non-owner messages produce no reply."""
    update = _make_update("/cmd", args, user_id=12345)
    handler = getattr(handlers, handler_name)

    await handler(update, _make_context(args))

    update.message.reply_text.assert_not_awaited()


# ---------------------------------------------------------------------------
# Generic error handling (AC-019)
# ---------------------------------------------------------------------------

async def test_add_unexpected_exception_is_caught(handlers, conn, monkeypatch):
    """AC-019: unexpected exception -> GENERIC_ERROR, bot does not crash."""
    from app.storage.repositories import ChannelRepo

    async def boom(self, *args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(ChannelRepo, "add", boom)

    update = _make_update("/add @bbcrussian", ["@bbcrussian"])
    await handlers.add_handler(update, _make_context(["@bbcrussian"]))

    update.message.reply_text.assert_awaited_once_with(handlers.messages.GENERIC_ERROR)

    error_rows = await conn.execute_fetchall("SELECT * FROM errors")
    assert error_rows[0]["scope"] == "add_channel"
    assert error_rows[0]["message"] == "boom"


# ---------------------------------------------------------------------------
# Feature 003 — wiring validate_channel() into /add (AC-040 – AC-043)
# ---------------------------------------------------------------------------

async def test_add_validates_channel_before_saving(handlers):
    """AC-040: /add calls validate_channel() before ChannelRepo.add()."""
    from app.reader.posts import ChannelInfo

    with patch(
        "app.bot.handlers.validate_channel",
        new=AsyncMock(return_value=ChannelInfo(username="bbcrussian", title="BBC Russian", is_public=True)),
    ) as mock_validate:
        update = _make_update("/add @bbcrussian", ["@bbcrussian"])
        await handlers.add_handler(update, _make_context(["@bbcrussian"]))

    mock_validate.assert_awaited_once_with("bbcrussian")
    msg = update.message.reply_text.await_args.args[0]
    assert "bbcrussian" in msg


async def test_add_channel_not_found_on_telegram(handlers, conn):
    """AC-041: ChannelNotFound -> CHANNEL_NOT_FOUND_ON_TELEGRAM, no row inserted."""
    from app.reader.posts import ChannelNotFound
    from app.storage.repositories import ChannelRepo

    with patch(
        "app.bot.handlers.validate_channel",
        new=AsyncMock(side_effect=ChannelNotFound("bbcrussian")),
    ):
        update = _make_update("/add @bbcrussian", ["@bbcrussian"])
        await handlers.add_handler(update, _make_context(["@bbcrussian"]))

    update.message.reply_text.assert_awaited_once_with(
        handlers.messages.CHANNEL_NOT_FOUND_ON_TELEGRAM.format(username="bbcrussian")
    )

    repo = ChannelRepo(conn)
    assert await repo.count_active() == 0


async def test_add_channel_not_public(handlers):
    """AC-042: ChannelNotPublic -> CHANNEL_NOT_PUBLIC."""
    from app.reader.posts import ChannelNotPublic

    with patch(
        "app.bot.handlers.validate_channel",
        new=AsyncMock(side_effect=ChannelNotPublic("bbcrussian")),
    ):
        update = _make_update("/add @bbcrussian", ["@bbcrussian"])
        await handlers.add_handler(update, _make_context(["@bbcrussian"]))

    update.message.reply_text.assert_awaited_once_with(
        handlers.messages.CHANNEL_NOT_PUBLIC.format(username="bbcrussian")
    )


async def test_add_stores_title_from_channel_info(handlers, conn):
    """AC-043: on success, title from ChannelInfo is stored, not NULL."""
    from app.reader.posts import ChannelInfo
    from app.storage.repositories import ChannelRepo

    with patch(
        "app.bot.handlers.validate_channel",
        new=AsyncMock(return_value=ChannelInfo(username="bbcrussian", title="BBC Russian", is_public=True)),
    ):
        update = _make_update("/add @bbcrussian", ["@bbcrussian"])
        await handlers.add_handler(update, _make_context(["@bbcrussian"]))

    repo = ChannelRepo(conn)
    channels = await repo.list_active()
    assert channels[0].title == "BBC Russian"
