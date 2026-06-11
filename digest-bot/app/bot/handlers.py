"""Telegram bot command handlers."""

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app import config
from app.bot import messages
from app.digest.collector import collect_posts
from app.digest.filter import filter_posts
from app.digest.formatter import ChannelDigestMeta, format_channel_digest
from app.digest.summarizer import DigestResult, summarize
from app.llm.factory import get_llm_client
from app.reader import posts
from app.reader.posts import ChannelInfo, ChannelNotFound, ChannelNotPublic
from app.reader.telethon_client import ensure_connected, get_client
from app.storage import db
from app.storage.repositories import (
    Channel,
    ChannelAlreadyExists,
    ChannelLimitReached,
    ChannelRepo,
    DigestRunRepo,
    LLMUsageRepo,
    PostsCacheRepo,
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


# ---------------------------------------------------------------------------
# /digest
# ---------------------------------------------------------------------------

async def digest_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await owner_guard(update, context):
        return
    if update.message is None:
        return

    args = context.args or []

    channel_username: str | None = None
    if len(args) == 1:
        days_arg = args[0]
    elif len(args) == 2:
        channel_username = args[0].lstrip("@").lower()
        days_arg = args[1]
    else:
        await update.message.reply_text(messages.DIGEST_USAGE, parse_mode=ParseMode.HTML)
        return

    if not days_arg.isdigit() or not (1 <= int(days_arg) <= config.MAX_DAYS):
        await update.message.reply_text(
            messages.DIGEST_INVALID_DAYS.format(max_days=config.MAX_DAYS)
        )
        return
    days = int(days_arg)

    async with db.get_connection() as conn:
        channels = await ChannelRepo(conn).list_active()

    if channel_username is not None:
        channels = [c for c in channels if c.username == channel_username]
        if not channels:
            await update.message.reply_text(
                messages.CHANNEL_NOT_FOUND.format(username=channel_username)
            )
            return
    elif not channels:
        await update.message.reply_text(messages.CHANNELS_EMPTY)
        return

    await update.message.reply_text(messages.DIGEST_STARTED)
    asyncio.create_task(_run_digest(update, channels, days, channel_username))


async def _run_digest(
    update: Update,
    channels: list[Channel],
    days: int,
    channel_filter: str | None,
) -> None:
    async with db.get_connection() as conn:
        run_repo = DigestRunRepo(conn)
        run_id = await run_repo.create(days=days, channel_filter=channel_filter)

        try:
            since = datetime.now(timezone.utc) - timedelta(days=days)
            cache_repo = PostsCacheRepo(conn)
            client = get_client()
            await ensure_connected(client)
            llm = get_llm_client()

            total_fetched = 0
            total_included = 0

            for channel in channels:
                collected = await collect_posts([channel], since, cache_repo, client)
                filtered = filter_posts(collected.posts)
                total_fetched += len(collected.posts)
                total_included += len(filtered)

                if collected.failed_channels:
                    digest_result = DigestResult(items=[], llm_result=None, prompt_version="")
                    meta = ChannelDigestMeta(
                        days=days,
                        posts_fetched=len(collected.posts),
                        posts_included=0,
                        error="не удалось получить посты канала",
                    )
                elif not filtered:
                    digest_result = DigestResult(items=[], llm_result=None, prompt_version="")
                    meta = ChannelDigestMeta(
                        days=days, posts_fetched=len(collected.posts), posts_included=0
                    )
                else:
                    digest_result = await summarize(filtered, llm)
                    meta = ChannelDigestMeta(
                        days=days, posts_fetched=len(collected.posts), posts_included=len(filtered)
                    )

                for message_text in format_channel_digest(channel.username, digest_result, meta):
                    await update.message.reply_text(
                        message_text,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True,
                    )

                if digest_result.llm_result is not None:
                    await LLMUsageRepo(conn).record(
                        digest_run_id=run_id,
                        provider=config.LLM_PROVIDER,
                        model=digest_result.llm_result.model,
                        prompt_version=digest_result.prompt_version,
                        input_tokens=digest_result.llm_result.input_tokens,
                        output_tokens=digest_result.llm_result.output_tokens,
                    )

            await run_repo.complete(
                run_id, posts_fetched=total_fetched, posts_included=total_included
            )
        except Exception as exc:
            logger.exception("Digest run %d failed", run_id)
            await run_repo.fail(run_id, str(exc))
            await update.message.reply_text(messages.GENERIC_ERROR)
