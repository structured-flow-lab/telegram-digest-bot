"""Telegram bot command handlers."""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app import config
from app.bot import messages

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Owner guard
# ---------------------------------------------------------------------------

async def owner_guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Return True if the sender is the owner; silently ignore otherwise."""
    user = update.effective_user
    if user is None or user.id != config.OWNER_TELEGRAM_ID:
        logger.debug(
            "Ignored message from user_id=%s (not the owner)",
            user.id if user else "unknown",
        )
        return False
    return True


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await owner_guard(update, context):
        return
    assert update.message is not None
    await update.message.reply_text(messages.START)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await owner_guard(update, context):
        return
    assert update.message is not None
    await update.message.reply_text(messages.HELP, parse_mode=ParseMode.HTML)
