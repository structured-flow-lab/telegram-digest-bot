"""Database migrations — run once at startup."""

import logging

import aiosqlite

logger = logging.getLogger(__name__)

_CREATE_CHANNELS = """
CREATE TABLE IF NOT EXISTS channels (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL UNIQUE,   -- e.g. "bbcrussian" (without @)
    title       TEXT,
    added_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    is_active   INTEGER NOT NULL DEFAULT 1
);
"""

_CREATE_POSTS_CACHE = """
CREATE TABLE IF NOT EXISTS posts_cache (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id   INTEGER NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    telegram_msg_id INTEGER NOT NULL,
    posted_at    TEXT    NOT NULL,         -- ISO-8601 UTC
    text         TEXT,
    url          TEXT,
    fetched_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(channel_id, telegram_msg_id)
);
"""

_CREATE_DIGEST_RUNS = """
CREATE TABLE IF NOT EXISTS digest_runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    finished_at  TEXT,
    days         INTEGER NOT NULL,
    channel_filter TEXT,                   -- NULL = all channels
    posts_fetched INTEGER,
    posts_included INTEGER,
    status       TEXT    NOT NULL DEFAULT 'running',  -- running | ok | error
    error_msg    TEXT
);
"""

_CREATE_LLM_USAGE = """
CREATE TABLE IF NOT EXISTS llm_usage (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    digest_run_id INTEGER NOT NULL REFERENCES digest_runs(id) ON DELETE CASCADE,
    provider      TEXT    NOT NULL,
    model         TEXT    NOT NULL,
    prompt_version TEXT,
    input_tokens  INTEGER,
    output_tokens INTEGER,
    called_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

_MIGRATIONS = [
    _CREATE_CHANNELS,
    _CREATE_POSTS_CACHE,
    _CREATE_DIGEST_RUNS,
    _CREATE_LLM_USAGE,
]


async def run_migrations(conn: aiosqlite.Connection) -> None:
    """Create all tables if they do not exist yet."""
    for statement in _MIGRATIONS:
        await conn.execute(statement)
    await conn.commit()
    logger.info("Database migrations applied")
