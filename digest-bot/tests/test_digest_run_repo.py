"""Feature 004 — AC-060 – AC-063 — DigestRunRepo + LLMUsageRepo (app/storage/repositories.py)."""

import aiosqlite
import pytest

from app.storage.migrations import run_migrations
from app.storage.repositories import DigestRunRepo, LLMUsageRepo


@pytest.fixture
async def conn():
    async with aiosqlite.connect(":memory:") as c:
        c.row_factory = aiosqlite.Row
        await run_migrations(c)
        yield c


@pytest.fixture
def digest_run_repo(conn):
    return DigestRunRepo(conn)


@pytest.fixture
def llm_usage_repo(conn):
    return LLMUsageRepo(conn)


async def _row(conn, run_id):
    rows = await conn.execute_fetchall(
        "SELECT * FROM digest_runs WHERE id = ?", (run_id,)
    )
    return rows[0]


async def test_create_inserts_running_row(conn, digest_run_repo):
    run_id = await digest_run_repo.create(days=7, channel_filter=None)

    row = await _row(conn, run_id)
    assert row["status"] == "running"
    assert row["days"] == 7
    assert row["channel_filter"] is None
    assert row["finished_at"] is None


async def test_create_with_channel_filter(conn, digest_run_repo):
    run_id = await digest_run_repo.create(days=3, channel_filter="bbcrussian")

    row = await _row(conn, run_id)
    assert row["channel_filter"] == "bbcrussian"


async def test_complete_sets_ok_and_counts(conn, digest_run_repo):
    run_id = await digest_run_repo.create(days=7, channel_filter=None)

    await digest_run_repo.complete(run_id, posts_fetched=42, posts_included=10)

    row = await _row(conn, run_id)
    assert row["status"] == "ok"
    assert row["posts_fetched"] == 42
    assert row["posts_included"] == 10
    assert row["finished_at"] is not None


async def test_fail_sets_error_and_message(conn, digest_run_repo):
    run_id = await digest_run_repo.create(days=7, channel_filter=None)

    await digest_run_repo.fail(run_id, "boom")

    row = await _row(conn, run_id)
    assert row["status"] == "error"
    assert row["error_msg"] == "boom"
    assert row["finished_at"] is not None


async def test_record_inserts_usage_row(conn, digest_run_repo, llm_usage_repo):
    run_id = await digest_run_repo.create(days=7, channel_filter=None)

    await llm_usage_repo.record(
        digest_run_id=run_id,
        provider="claude",
        model="claude-haiku-4-5",
        prompt_version="digest_v1",
        input_tokens=100,
        output_tokens=200,
    )

    rows = await conn.execute_fetchall(
        "SELECT * FROM llm_usage WHERE digest_run_id = ?", (run_id,)
    )
    row = rows[0]
    assert row["provider"] == "claude"
    assert row["model"] == "claude-haiku-4-5"
    assert row["prompt_version"] == "digest_v1"
    assert row["input_tokens"] == 100
    assert row["output_tokens"] == 200
