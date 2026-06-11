"""Telegram bot command handlers."""

import logging
import re

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app import config
from app.bot import messages
from app.reader import posts
from app.reader.posts import ChannelInfo, ChannelNotFound, ChannelNotPublic
from app.reader.telethon_client import ensure_connected, get_client
from app.storage import db
from app.storage.repositories import (
    ChannelAlreadyExists,
    ChannelLimitReached,
    ChannelRepo,
)

logger = logging.getLogger(__name__)

USERNAME_RE = re.compile(r"^@?[A-Za-z0-9_]{5,32}$")


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
    if update.message is None:
        return
    await update.message.reply_text(messages.START)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await owner_guard(update, context):
        return
    if update.message is None:
        return
    await update.message.reply_text(messages.HELP, parse_mode=ParseMode.HTML)


# ---------------------------------------------------------------------------
# Channel validation (Telethon)
# ---------------------------------------------------------------------------

async def validate_channel(username: str) -> ChannelInfo:
    """Resolve `username` on Telegram via the shared Telethon client."""
    client = get_client()
    await ensure_connected(client)
    return await posts.validate_channel(username, client)


# ---------------------------------------------------------------------------
# /add /remove /channels
# ---------------------------------------------------------------------------

async def add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await owner_guard(update, context):
        return
    if update.message is None:
        return

    args = context.args or []
    if not args or not USERNAME_RE.match(args[0]):
        await update.message.reply_text(messages.CHANNEL_INVALID_FORMAT)
        return

    username = args[0].lstrip("@").lower()

    try:
        info = await validate_channel(username)

        async with db.get_connection() as conn:
            channel = await ChannelRepo(conn).add(username, title=info.title)
    except ChannelNotFound:
        await update.message.reply_text(
            messages.CHANNEL_NOT_FOUND_ON_TELEGRAM.format(username=username)
        )
        return
    except ChannelNotPublic:
        await update.message.reply_text(
            messages.CHANNEL_NOT_PUBLIC.format(username=username)
        )
        return
    except ChannelAlreadyExists:
        await update.message.reply_text(
            messages.CHANNEL_ALREADY_EXISTS.format(username=username)
        )
        return
    except ChannelLimitReached:
        await update.message.reply_text(
            messages.CHANNEL_LIMIT_REACHED.format(limit=config.MAX_CHANNELS)
        )
        return
    except Exception:
        logger.exception("Failed to add channel %r", username)
        await update.message.reply_text(messages.GENERIC_ERROR)
        return

    await update.message.reply_text(messages.CHANNEL_ADDED.format(username=channel.username))


async def remove_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await owner_guard(update, context):
        return
    if update.message is None:
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(messages.CHANNEL_INVALID_FORMAT)
        return

    username = args[0].lstrip("@").lower()

    try:
        async with db.get_connection() as conn:
            removed = await ChannelRepo(conn).remove(username)
    except Exception:
        logger.exception("Failed to remove channel %r", username)
        await update.message.reply_text(messages.GENERIC_ERROR)
        return

    if removed:
        await update.message.reply_text(messages.CHANNEL_REMOVED.format(username=username))
    else:
        await update.message.reply_text(messages.CHANNEL_NOT_FOUND.format(username=username))


async def channels_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await owner_guard(update, context):
        return
    if update.message is None:
        return

    try:
        async with db.get_connection() as conn:
            channels = await ChannelRepo(conn).list_active()
    except Exception:
        logger.exception("Failed to list channels")
        await update.message.reply_text(messages.GENERIC_ERROR)
        return

    if not channels:
        await update.message.reply_text(messages.CHANNELS_EMPTY)
        return

    lines = [messages.CHANNELS_HEADER] + [f"@{channel.username}" for channel in channels]
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
