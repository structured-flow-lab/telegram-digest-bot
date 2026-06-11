"""Data-access repositories."""

from dataclasses import dataclass
from datetime import datetime

import aiosqlite

from app import config
from app.reader.posts import Post


@dataclass
class Channel:
    id: int
    username: str
    title: str | None
    added_at: str
    is_active: int


@dataclass
class CachedPost:
    telegram_msg_id: int
    posted_at: datetime
    text: str
    url: str


class ChannelAlreadyExists(Exception):
    """Raised when adding a channel whose username already exists."""


class ChannelLimitReached(Exception):
    """Raised when adding a channel would exceed config.MAX_CHANNELS."""


def _normalise_username(username: str) -> str:
    return username.lstrip("@").lower()


class ChannelRepo:
    """Repository for the `channels` table."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def add(self, username: str, title: str | None) -> Channel:
        normalised = _normalise_username(username)

        existing = await self._conn.execute_fetchall(
            "SELECT id FROM channels WHERE LOWER(username) = ?",
            (normalised,),
        )
        if existing:
            raise ChannelAlreadyExists(normalised)

        if await self.count_active() >= config.MAX_CHANNELS:
            raise ChannelLimitReached(normalised)

        cursor = await self._conn.execute(
            "INSERT INTO channels (username, title) VALUES (?, ?)",
            (normalised, title),
        )
        await self._conn.commit()

        row = await self._conn.execute_fetchall(
            "SELECT id, username, title, added_at, is_active FROM channels WHERE id = ?",
            (cursor.lastrowid,),
        )
        record = row[0]
        return Channel(
            id=record["id"],
            username=record["username"],
            title=record["title"],
            added_at=record["added_at"],
            is_active=record["is_active"],
        )

    async def remove(self, username: str) -> bool:
        normalised = _normalise_username(username)
        cursor = await self._conn.execute(
            "DELETE FROM channels WHERE LOWER(username) = ?",
            (normalised,),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def list_active(self) -> list[Channel]:
        rows = await self._conn.execute_fetchall(
            "SELECT id, username, title, added_at, is_active "
            "FROM channels WHERE is_active = 1 ORDER BY added_at ASC"
        )
        return [
            Channel(
                id=row["id"],
                username=row["username"],
                title=row["title"],
                added_at=row["added_at"],
                is_active=row["is_active"],
            )
            for row in rows
        ]

    async def count_active(self) -> int:
        rows = await self._conn.execute_fetchall(
            "SELECT COUNT(*) AS cnt FROM channels WHERE is_active = 1"
        )
        return rows[0]["cnt"]


class PostsCacheRepo:
    """Repository for the `posts_cache` table."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def upsert_posts(self, channel_id: int, posts: list[Post]) -> int:
        inserted = 0
        for post in posts:
            cursor = await self._conn.execute(
                "INSERT OR IGNORE INTO posts_cache "
                "(channel_id, telegram_msg_id, posted_at, text, url) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    channel_id,
                    post.telegram_msg_id,
                    post.posted_at.isoformat(),
                    post.text,
                    post.url,
                ),
            )
            if cursor.rowcount > 0:
                inserted += cursor.rowcount
        await self._conn.commit()
        return inserted

    async def latest_cached_at(self, channel_id: int) -> datetime | None:
        rows = await self._conn.execute_fetchall(
            "SELECT MAX(posted_at) AS latest FROM posts_cache WHERE channel_id = ?",
            (channel_id,),
        )
        latest = rows[0]["latest"]
        if latest is None:
            return None
        return datetime.fromisoformat(latest)

    async def get_cached_since(
        self, channel_id: int, since: datetime, limit: int
    ) -> list[CachedPost]:
        rows = await self._conn.execute_fetchall(
            "SELECT telegram_msg_id, posted_at, text, url FROM posts_cache "
            "WHERE channel_id = ? AND posted_at >= ? "
            "ORDER BY posted_at ASC LIMIT ?",
            (channel_id, since.isoformat(), limit),
        )
        return [
            CachedPost(
                telegram_msg_id=row["telegram_msg_id"],
                posted_at=datetime.fromisoformat(row["posted_at"]),
                text=row["text"],
                url=row["url"],
            )
            for row in rows
        ]


class DigestRunRepo:
    """Repository for the `digest_runs` table."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def create(self, days: int, channel_filter: str | None) -> int:
        cursor = await self._conn.execute(
            "INSERT INTO digest_runs (days, channel_filter) VALUES (?, ?)",
            (days, channel_filter),
        )
        await self._conn.commit()
        return cursor.lastrowid

    async def complete(self, run_id: int, posts_fetched: int, posts_included: int) -> None:
        await self._conn.execute(
            "UPDATE digest_runs SET status = 'ok', finished_at = datetime('now'), "
            "posts_fetched = ?, posts_included = ? WHERE id = ?",
            (posts_fetched, posts_included, run_id),
        )
        await self._conn.commit()

    async def fail(self, run_id: int, error_msg: str) -> None:
        await self._conn.execute(
            "UPDATE digest_runs SET status = 'error', finished_at = datetime('now'), "
            "error_msg = ? WHERE id = ?",
            (error_msg, run_id),
        )
        await self._conn.commit()


class LLMUsageRepo:
    """Repository for the `llm_usage` table."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def record(
        self,
        digest_run_id: int,
        provider: str,
        model: str,
        prompt_version: str | None,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        await self._conn.execute(
            "INSERT INTO llm_usage "
            "(digest_run_id, provider, model, prompt_version, input_tokens, output_tokens) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (digest_run_id, provider, model, prompt_version, input_tokens, output_tokens),
        )
        await self._conn.commit()


class ErrorRepo:
    """Repository for the `errors` table."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def log(self, scope: str, message: str) -> None:
        await self._conn.execute(
            "INSERT INTO errors (scope, message) VALUES (?, ?)",
            (scope, message),
        )
        await self._conn.commit()
