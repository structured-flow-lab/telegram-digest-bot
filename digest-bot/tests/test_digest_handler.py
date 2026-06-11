"""Feature 004 — AC-070 – AC-075 — /digest handler (app/bot/handlers.py)."""

import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
import pytest

from app.digest.collector import CollectResult
from app.digest.summarizer import DigestCluster, DigestResult
from app.llm.base import LLMResult
from app.storage.migrations import run_migrations


def _make_update(args: list[str], user_id: int = 999):
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


def _make_context(args: list[str]):
    context = MagicMock()
    context.args = args
    return context


def _reset_handlers_module():
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

    @asynccontextmanager
    async def fake_get_connection():
        yield conn

    monkeypatch.setattr(h.db, "get_connection", fake_get_connection)
    monkeypatch.setattr(h, "get_client", lambda: MagicMock())
    monkeypatch.setattr(h, "ensure_connected", AsyncMock())
    return h


async def _add_channel(handlers, conn, username):
    from app.storage.repositories import ChannelRepo

    return await ChannelRepo(conn).add(username, title=username)


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------

async def test_no_args_returns_usage(handlers):
    update = _make_update([])
    await handlers.digest_handler(update, _make_context([]))

    update.message.reply_text.assert_awaited_once()
    args, kwargs = update.message.reply_text.await_args
    assert args[0] == handlers.messages.DIGEST_USAGE


async def test_too_many_args_returns_usage(handlers):
    update = _make_update(["@a", "7", "extra"])
    await handlers.digest_handler(update, _make_context(["@a", "7", "extra"]))

    args, _ = update.message.reply_text.await_args
    assert args[0] == handlers.messages.DIGEST_USAGE


async def test_non_numeric_days_returns_invalid_days(handlers):
    update = _make_update(["abc"])
    await handlers.digest_handler(update, _make_context(["abc"]))

    update.message.reply_text.assert_awaited_once_with(
        handlers.messages.DIGEST_INVALID_DAYS.format(max_days=handlers.config.MAX_DAYS)
    )


async def test_days_out_of_range_returns_invalid_days(handlers):
    update = _make_update([str(handlers.config.MAX_DAYS + 1)])
    await handlers.digest_handler(update, _make_context([str(handlers.config.MAX_DAYS + 1)]))

    update.message.reply_text.assert_awaited_once_with(
        handlers.messages.DIGEST_INVALID_DAYS.format(max_days=handlers.config.MAX_DAYS)
    )


async def test_no_channels_returns_channels_empty(handlers):
    update = _make_update(["7"])
    await handlers.digest_handler(update, _make_context(["7"]))

    update.message.reply_text.assert_awaited_once_with(handlers.messages.CHANNELS_EMPTY)


async def test_unknown_channel_filter_returns_channel_not_found(handlers, conn):
    await _add_channel(handlers, conn, "knownchan")

    update = _make_update(["@unknownchan", "7"])
    await handlers.digest_handler(update, _make_context(["@unknownchan", "7"]))

    update.message.reply_text.assert_awaited_once_with(
        handlers.messages.CHANNEL_NOT_FOUND.format(username="unknownchan")
    )


# ---------------------------------------------------------------------------
# Happy path — starts the pipeline
# ---------------------------------------------------------------------------

async def test_valid_request_acknowledges_and_starts_task(handlers, conn):
    await _add_channel(handlers, conn, "knownchan")

    update = _make_update(["7"])

    with patch.object(handlers.asyncio, "create_task") as mock_create_task:
        await handlers.digest_handler(update, _make_context(["7"]))

    update.message.reply_text.assert_awaited_once_with(handlers.messages.DIGEST_STARTED)
    mock_create_task.assert_called_once()
    mock_create_task.call_args.args[0].close()


# ---------------------------------------------------------------------------
# _run_digest pipeline
# ---------------------------------------------------------------------------

@pytest.fixture
def pipeline_mocks(handlers):
    collected = CollectResult(posts=[], failed_channels=[])
    digest_result = DigestResult(clusters=[], llm_result=None)

    with patch.object(handlers, "collect_posts", AsyncMock(return_value=collected)) as m_collect, \
         patch.object(handlers, "filter_posts", return_value=[]) as m_filter, \
         patch.object(handlers, "get_llm_client", return_value=AsyncMock()) as m_get_llm, \
         patch.object(handlers, "summarize", AsyncMock(return_value=digest_result)) as m_summarize, \
         patch.object(handlers, "format_digest", return_value=["digest message"]) as m_format:
        yield {
            "collected": collected,
            "digest_result": digest_result,
            "collect": m_collect,
            "filter": m_filter,
            "get_llm": m_get_llm,
            "summarize": m_summarize,
            "format": m_format,
        }


async def test_run_digest_success_records_run_and_replies(handlers, conn, pipeline_mocks):
    channel = await _add_channel(handlers, conn, "knownchan")
    update = _make_update(["7"])

    await handlers._run_digest(update, [channel], days=7, channel_filter=None)

    update.message.reply_text.assert_awaited_with(
        "digest message", parse_mode=handlers.ParseMode.HTML, disable_web_page_preview=True
    )

    rows = await conn.execute_fetchall("SELECT * FROM digest_runs")
    assert rows[0]["status"] == "ok"
    assert rows[0]["posts_included"] == 0


async def test_run_digest_records_llm_usage_when_present(handlers, conn, pipeline_mocks):
    channel = await _add_channel(handlers, conn, "knownchan")
    update = _make_update(["7"])

    llm_result = LLMResult(text="{}", input_tokens=11, output_tokens=22, model="claude-haiku-4-5")
    pipeline_mocks["summarize"].return_value = DigestResult(
        clusters=[DigestCluster(title="T", summary="S", post_urls=[])],
        llm_result=llm_result,
    )

    await handlers._run_digest(update, [channel], days=7, channel_filter=None)

    rows = await conn.execute_fetchall("SELECT * FROM llm_usage")
    assert len(rows) == 1
    assert rows[0]["input_tokens"] == 11
    assert rows[0]["output_tokens"] == 22


async def test_run_digest_failure_marks_run_as_error(handlers, conn, pipeline_mocks):
    channel = await _add_channel(handlers, conn, "knownchan")
    update = _make_update(["7"])

    pipeline_mocks["collect"].side_effect = RuntimeError("boom")

    await handlers._run_digest(update, [channel], days=7, channel_filter=None)

    rows = await conn.execute_fetchall("SELECT * FROM digest_runs")
    assert rows[0]["status"] == "error"
    assert rows[0]["error_msg"] == "boom"

    update.message.reply_text.assert_awaited_with(handlers.messages.GENERIC_ERROR)
