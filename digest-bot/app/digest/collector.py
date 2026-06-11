"""Collect posts for a digest — cache + fresh fetch, merged and capped."""

import logging
from dataclasses import dataclass
from datetime import datetime

from app import config
from app.reader.posts import ChannelFetchError, fetch_posts
from app.reader.telethon_client import ensure_connected
from app.storage.repositories import CachedPost, Channel, PostsCacheRepo

logger = logging.getLogger(__name__)


@dataclass
class CollectResult:
    posts: list[CachedPost]
    failed_channels: list[str]


async def collect_posts(
    channels: list[Channel],
    since: datetime,
    cache_repo: PostsCacheRepo,
    client,
) -> CollectResult:
    await ensure_connected(client)

    all_posts: list[CachedPost] = []
    failed_channels: list[str] = []

    for channel in channels:
        try:
            latest = await cache_repo.latest_cached_at(channel.id)
            fetch_since = latest if latest is not None else since
            new_posts = await fetch_posts(
                channel.username, fetch_since, config.MAX_POSTS_PER_CHANNEL, client
            )
            if new_posts:
                await cache_repo.upsert_posts(channel.id, new_posts)
        except ChannelFetchError:
            logger.exception("Failed to fetch posts for channel %s", channel.username)
            failed_channels.append(channel.username)

        channel_posts = await cache_repo.get_cached_since(
            channel.id, since, config.MAX_POSTS_PER_CHANNEL
        )
        all_posts.extend(channel_posts)

    all_posts.sort(key=lambda p: p.posted_at)
    if len(all_posts) > config.MAX_POSTS_PER_DIGEST:
        all_posts = all_posts[-config.MAX_POSTS_PER_DIGEST :]

    return CollectResult(posts=all_posts, failed_channels=failed_channels)
