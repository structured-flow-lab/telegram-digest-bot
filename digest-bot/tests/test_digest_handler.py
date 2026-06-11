"""Feature 004 — AC-060 – AC-067 — /digest handler + run_digest()."""

import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import aiosqlite
import pytest

from app.storage.migrations import run_migrations
from app.storage.repositories import ChannelRepo


def _make_update(args, user_id=999):
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.effective_chat = MagicMock()
    update.effective_chat.id = 999
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


def _make_context(args, bot=None):
    context = MagicMock()
    context.args = args
    context.bot = bot or MagicMock()
    context.bot.send_message = AsyncMock()
    return context


@pytest.fixture(autouse=True)
def ensure_config(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake:token")
    monkeypatch.setenv("OWNER_TELEGRAM_ID", "999")
    sys.modules.pop("app.config", None)
    sys.modules.pop("app.bot.handlers", None)
    yield
    sys.modules.pop("app.config", None)
    sys.modules.pop("app.bot.handlers", None)


@pytest.fixture
async def conn():
    async with aiosqlite.connect(":memory:") as c:
        c.row_factory = aiosqlite.Row
        await run_migrations(c)
        yield c


@pytest.fixture
def handlers(conn, monkeypatch):
    from app.bot import handlers as h

    @asynccontextmanager
    async def fake_get_connection():
        yield conn

    monkeypatch.setattr(h.db, "get_connection", fake_get_connection)
    return h


# ---------------------------------------------------------------------------
# AC-060 / AC-061 / AC-062 — input validation
# ---------------------------------------------------------------------------

async def test_digest_no_args_shows_usage(handlers):
    """AC-060: /digest with no arguments -> DIGEST_USAGE, no run started."""
    update = _make_update([])
    await handlers.digest_handler(update, _make_context([]))

    update.message.reply_text.assert_awaited_once_with(handlers.messages.DIGEST_USAGE)


@pytest.mark.parametrize("args", [["0"], ["-1"], ["31"], ["abc"]])
async def test_digest_invalid_days(handlers, args):
    """AC-061: days outside 1..MAX_DAYS or non-integer -> DIGEST_INVALID_DAYS."""
    update = _make_update(args)
    await handlers.digest_handler(update, _make_context(args))

    update.message.reply_text.assert_awaited_once_with(
        handlers.messages.DIGEST_INVALID_DAYS.format(max_days=handlers.config.MAX_DAYS)
    )


async def test_digest_unknown_channel(handlers):
    """AC-062: /digest @channel <days> for an unknown channel -> CHANNEL_NOT_FOUND."""
    update = _make_update(["@ghost", "7"])
    await handlers.digest_handler(update, _make_context(["@ghost", "7"]))

    update.message.reply_text.assert_awaited_once_with(
        handlers.messages.CHANNEL_NOT_FOUND.format(username="ghost")
    )


# ---------------------------------------------------------------------------
# AC-063 — non-blocking start
# ---------------------------------------------------------------------------

async def test_digest_valid_replies_started_and_schedules_run(handlers, monkeypatch):
    """AC-063: valid /digest replies DIGEST_STARTED and schedules run_digest()."""
    fake_run_digest = AsyncMock()
    monkeypatch.setattr(handlers, "run_digest", fake_run_digest)

    update = _make_update(["7"])
    context = _make_context(["7"])

    await handlers.digest_handler(update, context)

    update.message.reply_text.assert_awaited_once_with(handlers.messages.DIGEST_STARTED)
    fake_run_digest.assert_called_once()


# ---------------------------------------------------------------------------
# AC-064 / AC-065 / AC-066 — run_digest()
# ---------------------------------------------------------------------------

@pytest.fixture
async def channel(conn):
    repo = ChannelRepo(conn)
    return await repo.add("channel_a", title="Channel A")


async def test_run_digest_empty_result(handlers, conn, channel, monkeypatch):
    """AC-064: no posts after filtering -> empty digest sent, status='empty'."""
    monkeypatch.setattr(handlers, "collect_posts", AsyncMock(return_value=([], 0)))
    monkeypatch.setattr(handlers, "filter_posts", lambda posts: [])
    monkeypatch.setattr(handlers, "format_empty_digest", lambda channels: "nothing new")

    bot = MagicMock()
    bot.send_message = AsyncMock()

    await handlers.run_digest(bot=bot, chat_id=999, days=7, channel_filter=None)

    bot.send_message.assert_awaited_once()
    assert bot.send_message.await_args.kwargs.get("text") == "nothing new" or \
        bot.send_message.await_args.args[-1] == "nothing new"

    rows = await conn.execute_fetchall("SELECT status, posts_included FROM digest_runs")
    assert rows[0]["status"] == "empty"
    assert rows[0]["posts_included"] == 0


async def test_run_digest_success(handlers, conn, channel, monkeypatch):
    """AC-065: non-empty digest -> summarize, record usage, send formatted digest, status='ok'."""
    from app.digest.collector import CollectedPost
    from app.llm.base import LLMResult

    posts = [
        CollectedPost(
            channel_username="channel_a",
            telegram_msg_id=1,
            posted_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            text="x" * 120,
            url="https://t.me/channel_a/1",
        )
    ]
    llm_result = LLMResult(text="summary", input_tokens=10, output_tokens=5, model="claude-haiku-4-5")

    monkeypatch.setattr(handlers, "collect_posts", AsyncMock(return_value=(posts, 1)))
    monkeypatch.setattr(handlers, "filter_posts", lambda p: p)
    monkeypatch.setattr(handlers, "get_llm_client", lambda: MagicMock())
    monkeypatch.setattr(handlers, "summarize", AsyncMock(return_value=llm_result))
    monkeypatch.setattr(handlers, "format_digest", lambda **kwargs: "formatted digest")

    bot = MagicMock()
    bot.send_message = AsyncMock()

    await handlers.run_digest(bot=bot, chat_id=999, days=7, channel_filter=None)

    bot.send_message.assert_awaited_once()
    sent_text = bot.send_message.await_args.kwargs.get("text") or bot.send_message.await_args.args[-1]
    assert sent_text == "formatted digest"

    run_row = (await conn.execute_fetchall("SELECT status, posts_included FROM digest_runs"))[0]
    assert run_row["status"] == "ok"
    assert run_row["posts_included"] == 1

    usage_row = (await conn.execute_fetchall("SELECT model, input_tokens, output_tokens FROM llm_usage"))[0]
    assert usage_row["model"] == "claude-haiku-4-5"
    assert usage_row["input_tokens"] == 10
    assert usage_row["output_tokens"] == 5


async def test_run_digest_error_is_caught(handlers, conn, channel, monkeypatch):
    """AC-066: any exception during the run -> status='error', DIGEST_ERROR sent, no crash."""
    monkeypatch.setattr(handlers, "collect_posts", AsyncMock(side_effect=RuntimeError("boom")))

    bot = MagicMock()
    bot.send_message = AsyncMock()

    await handlers.run_digest(bot=bot, chat_id=999, days=7, channel_filter=None)

    bot.send_message.assert_awaited_once()
    sent_text = bot.send_message.await_args.kwargs.get("text") or bot.send_message.await_args.args[-1]
    assert sent_text == handlers.messages.DIGEST_ERROR

    run_row = (await conn.execute_fetchall("SELECT status, error_msg FROM digest_runs"))[0]
    assert run_row["status"] == "error"
    assert run_row["error_msg"] == "boom"


# ---------------------------------------------------------------------------
# AC-067 — owner guard
# ---------------------------------------------------------------------------

async def test_digest_handler_respects_owner_guard(handlers):
    """AC-067: non-owner messages produce no reply."""
    update = _make_update(["7"], user_id=12345)

    await handlers.digest_handler(update, _make_context(["7"]))

    update.message.reply_text.assert_not_awaited()
