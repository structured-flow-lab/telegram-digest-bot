"""Feature 005 — AC-010 – AC-012 — app/bot/error_handler.py."""

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Update


@pytest.fixture(autouse=True)
def ensure_config(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake:token")
    monkeypatch.setenv("OWNER_TELEGRAM_ID", "999")
    sys.modules.pop("app.config", None)
    sys.modules.pop("app.bot.error_handler", None)
    yield
    sys.modules.pop("app.config", None)
    sys.modules.pop("app.bot.error_handler", None)


async def test_error_handler_logs_exception(caplog):
    """AC-010: logs context.error with traceback via logger.error(..., exc_info=...)."""
    from app.bot import error_handler as eh

    context = MagicMock()
    context.error = RuntimeError("boom")

    with caplog.at_level("ERROR", logger=eh.logger.name):
        await eh.error_handler(None, context)

    assert any("boom" in record.getMessage() or record.exc_info for record in caplog.records)


async def test_error_handler_notifies_owner_when_message_present():
    """AC-011: sends GENERIC_ERROR to the chat when update.effective_message is set."""
    from app.bot import error_handler as eh
    from app.bot import messages

    update = MagicMock(spec=Update)
    update.effective_message = MagicMock()
    update.effective_message.reply_text = AsyncMock()

    context = MagicMock()
    context.error = RuntimeError("boom")

    await eh.error_handler(update, context)

    update.effective_message.reply_text.assert_awaited_once_with(messages.GENERIC_ERROR)


async def test_error_handler_swallows_secondary_exception():
    """AC-011: an exception while notifying the owner is caught, not propagated."""
    from app.bot import error_handler as eh

    update = MagicMock(spec=Update)
    update.effective_message = MagicMock()
    update.effective_message.reply_text = AsyncMock(side_effect=RuntimeError("send failed"))

    context = MagicMock()
    context.error = RuntimeError("boom")

    await eh.error_handler(update, context)  # must not raise


async def test_error_handler_no_message_only_logs(caplog):
    """AC-012: update is None or has no effective_message -> only logs, no send attempt."""
    from app.bot import error_handler as eh

    context = MagicMock()
    context.error = RuntimeError("boom")

    with caplog.at_level("ERROR", logger=eh.logger.name):
        await eh.error_handler(None, context)
        await eh.error_handler(MagicMock(spec=Update, effective_message=None), context)

    # No exceptions raised; both calls logged.
    assert sum(1 for r in caplog.records if r.levelname == "ERROR") >= 2
