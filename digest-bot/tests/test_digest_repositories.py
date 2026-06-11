"""Feature 004 — AC-050 – AC-052 — DigestRunRepo, LLMUsageRepo (app/storage/repositories.py)."""

import aiosqlite
import pytest

from app.storage.migrations import run_migrations


@pytest.fixture
async def conn():
    async with aiosqlite.connect(":memory:") as c:
        c.row_factory = aiosqlite.Row
        await run_migrations(c)
        yield c


async def test_digest_run_repo_start_inserts_running_row(conn):
    """AC-050: start() inserts a row with status='running' and returns its id."""
    from app.storage.repositories import DigestRunRepo

    repo = DigestRunRepo(conn)
    run_id = await repo.start(days=7, channel_filter=None)

    assert isinstance(run_id, int)

    rows = await conn.execute_fetchall(
        "SELECT days, channel_filter, status, finished_at FROM digest_runs WHERE id = ?",
        (run_id,),
    )
    row = rows[0]
    assert row["days"] == 7
    assert row["channel_filter"] is None
    assert row["status"] == "running"
    assert row["finished_at"] is None


async def test_digest_run_repo_finish_updates_row(conn):
    """AC-051: finish() sets finished_at, posts_fetched/included, status, error_msg."""
    from app.storage.repositories import DigestRunRepo

    repo = DigestRunRepo(conn)
    run_id = await repo.start(days=7, channel_filter="channel_a")

    await repo.finish(run_id, posts_fetched=20, posts_included=8, status="ok")

    rows = await conn.execute_fetchall(
        "SELECT finished_at, posts_fetched, posts_included, status, error_msg "
        "FROM digest_runs WHERE id = ?",
        (run_id,),
    )
    row = rows[0]
    assert row["finished_at"] is not None
    assert row["posts_fetched"] == 20
    assert row["posts_included"] == 8
    assert row["status"] == "ok"
    assert row["error_msg"] is None


async def test_digest_run_repo_finish_with_error(conn):
    """AC-051: finish() with status='error' stores error_msg."""
    from app.storage.repositories import DigestRunRepo

    repo = DigestRunRepo(conn)
    run_id = await repo.start(days=7, channel_filter=None)

    await repo.finish(run_id, posts_fetched=0, posts_included=0, status="error", error_msg="boom")

    rows = await conn.execute_fetchall(
        "SELECT status, error_msg FROM digest_runs WHERE id = ?", (run_id,)
    )
    row = rows[0]
    assert row["status"] == "error"
    assert row["error_msg"] == "boom"


async def test_llm_usage_repo_records_usage(conn, monkeypatch):
    """AC-052: record() inserts a row derived from an LLMResult."""
    from app.storage.repositories import DigestRunRepo, LLMUsageRepo
    from app.llm.base import LLMResult
    from app.storage import repositories

    monkeypatch.setattr(repositories.config, "LLM_PROVIDER", "claude")

    digest_repo = DigestRunRepo(conn)
    run_id = await digest_repo.start(days=7, channel_filter=None)

    result = LLMResult(text="summary", input_tokens=123, output_tokens=45, model="claude-haiku-4-5")

    usage_repo = LLMUsageRepo(conn)
    await usage_repo.record(digest_run_id=run_id, result=result, prompt_version="digest_v1")

    rows = await conn.execute_fetchall(
        "SELECT digest_run_id, provider, model, prompt_version, input_tokens, output_tokens "
        "FROM llm_usage WHERE digest_run_id = ?",
        (run_id,),
    )
    row = rows[0]
    assert row["digest_run_id"] == run_id
    assert row["provider"] == "claude"
    assert row["model"] == "claude-haiku-4-5"
    assert row["prompt_version"] == "digest_v1"
    assert row["input_tokens"] == 123
    assert row["output_tokens"] == 45
