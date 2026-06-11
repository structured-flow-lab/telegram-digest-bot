"""Channel validation and post fetching via Telethon (feature-003)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from telethon.errors import FloodWaitError, UsernameInvalidError, UsernameNotOccupiedError


@dataclass
class ChannelInfo:
    username: str
    title: str
    is_public: bool


@dataclass
class Post:
    telegram_msg_id: int
    posted_at: datetime
    text: str
    url: str
    views: Optional[int] = None


class ChannelNotFound(Exception):
    pass


class ChannelNotPublic(Exception):
    pass


class ChannelFetchError(Exception):
    pass


async def validate_channel(username: str, client) -> ChannelInfo:
    try:
        entity = await client.get_entity(username)
    except (UsernameNotOccupiedError, UsernameInvalidError) as exc:
        raise ChannelNotFound(username) from exc

    if not getattr(entity, "username", None) or not getattr(entity, "broadcast", False):
        raise ChannelNotPublic(username)

    return ChannelInfo(username=entity.username, title=entity.title, is_public=True)


async def fetch_posts(username: str, since: datetime, limit: int, client) -> list[Post]:
    posts: list[Post] = []
    try:
        async for msg in client.iter_messages(username, offset_date=since, reverse=True, limit=limit):
            if not msg.message:
                continue
            if msg.date < since:
                continue
            posts.append(
                Post(
                    telegram_msg_id=msg.id,
                    posted_at=msg.date,
                    text=msg.message,
                    url=f"https://t.me/{username}/{msg.id}",
                    views=msg.views,
                )
            )
    except FloodWaitError as exc:
        raise ChannelFetchError(exc) from exc
    except Exception as exc:
        raise ChannelFetchError(exc) from exc

    posts.sort(key=lambda p: p.posted_at)
    return posts[:limit]
