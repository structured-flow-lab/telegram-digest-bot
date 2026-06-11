"""AC-010 – AC-014 — SQLite migrations."""

import pytest
import aiosqlite
from app.storage.migrations import run_migrations


async def _tables(conn: aiosqlite.Connection) -> set[str]:
    cur = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    rows = await cur.fetchall()
    return {row[0] for row in rows}


async def _columns(conn: aiosqlite.Connection, table: str) -> set[str]:
    cur = await conn.execute(f"PRAGMA table_info({table})")
    rows = await cur.fetchall()
    return {row[1] for row in rows}


@pytest.fixture
async def db():
    async with aiosqlite.connect(":memory:") as conn:
        yield conn


async def test_creates_channels_table(db):
    """AC-010."""
    await run_migrations(db)
    assert "channels" in await _tables(db)
    cols = await _columns(db, "channels")
    assert {"id", "username", "title", "added_at", "is_active"}.issubset(cols)


async def test_creates_posts_cache_table(db):
    """AC-011."""
    await run_migrations(db)
    assert "posts_cache" in await _tables(db)
    cols = await _columns(db, "posts_cache")
    assert {"id", "channel_id", "telegram_msg_id", "posted_at", "text", "url", "fetched_at"}.issubset(cols)


async def test_creates_digest_runs_table(db):
    """AC-012."""
    await run_migrations(db)
    assert "digest_runs" in await _tables(db)
    cols = await _columns(db, "digest_runs")
    assert {
        "id", "started_at", "finished_at", "days", "channel_filter",
        "posts_fetched", "posts_included", "status", "error_msg"
    }.issubset(cols)


async def test_creates_llm_usage_table(db):
    """AC-013."""
    await run_migrations(db)
    assert "llm_usage" in await _tables(db)
    cols = await _columns(db, "llm_usage")
    assert {
        "id", "digest_run_id", "provider", "model", "prompt_version",
        "input_tokens", "output_tokens", "called_at"
    }.issubset(cols)


async def test_creates_errors_table(db):
    """AC-200."""
    await run_migrations(db)
    assert "errors" in await _tables(db)
    cols = await _columns(db, "errors")
    assert {"id", "occurred_at", "scope", "message"}.issubset(cols)


async def test_migrations_idempotent(db):
    """AC-014: running migrations twice does not raise."""
    await run_migrations(db)
    await run_migrations(db)  # must not raise
