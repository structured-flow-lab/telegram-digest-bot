"""Feature 006 — AC-200 – AC-202 — ErrorRepo (app/storage/repositories.py)."""

import aiosqlite
import pytest

from app.storage.migrations import run_migrations
from app.storage.repositories import ErrorRepo


@pytest.fixture
async def conn():
    async with aiosqlite.connect(":memory:") as c:
        c.row_factory = aiosqlite.Row
        await run_migrations(c)
        yield c


@pytest.fixture
def error_repo(conn):
    return ErrorRepo(conn)


async def test_log_inserts_row(conn, error_repo):
    await error_repo.log("digest_run", "boom")

    rows = await conn.execute_fetchall("SELECT * FROM errors")
    row = rows[0]
    assert row["scope"] == "digest_run"
    assert row["message"] == "boom"
    assert row["occurred_at"] is not None


async def test_log_multiple_rows(conn, error_repo):
    await error_repo.log("add_channel", "first")
    await error_repo.log("digest_run", "second")

    rows = await conn.execute_fetchall("SELECT scope, message FROM errors ORDER BY id")
    assert [dict(r) for r in rows] == [
        {"scope": "add_channel", "message": "first"},
        {"scope": "digest_run", "message": "second"},
    ]
