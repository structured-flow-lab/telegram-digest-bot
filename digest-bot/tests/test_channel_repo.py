"""Feature 002 — AC-001 – AC-007 — ChannelRepo (app/storage/repositories.py)."""

import pytest
import aiosqlite

from app.storage.migrations import run_migrations
from app.storage.repositories import (
    ChannelRepo,
    ChannelAlreadyExists,
    ChannelLimitReached,
)


@pytest.fixture
async def conn():
    async with aiosqlite.connect(":memory:") as c:
        c.row_factory = aiosqlite.Row
        await run_migrations(c)
        yield c


@pytest.fixture
def repo(conn):
    return ChannelRepo(conn)


async def test_add_returns_channel_without_leading_at(repo):
    """AC-001."""
    channel = await repo.add("@vc_ru", title="VC.ru")
    assert channel.username == "vc_ru"
    assert channel.title == "VC.ru"
    assert channel.id is not None
    assert channel.is_active == 1


async def test_add_strips_at_when_absent(repo):
    """AC-001: works the same without a leading @."""
    channel = await repo.add("vc_ru", title="VC.ru")
    assert channel.username == "vc_ru"


async def test_add_duplicate_raises(repo):
    """AC-002: duplicate (case-insensitive) raises ChannelAlreadyExists."""
    await repo.add("vc_ru", title="VC.ru")
    with pytest.raises(ChannelAlreadyExists):
        await repo.add("VC_RU", title="VC.ru again")


async def test_add_over_limit_raises(repo, monkeypatch):
    """AC-003: raises ChannelLimitReached once count_active() >= MAX_CHANNELS."""
    from app.storage import repositories

    monkeypatch.setattr(repositories.config, "MAX_CHANNELS", 2)

    await repo.add("chan_one", title=None)
    await repo.add("chan_two", title=None)

    with pytest.raises(ChannelLimitReached):
        await repo.add("chan_three", title=None)


async def test_remove_existing_returns_true(repo):
    """AC-004."""
    await repo.add("vc_ru", title="VC.ru")
    assert await repo.remove("vc_ru") is True


async def test_remove_missing_returns_false(repo):
    """AC-004."""
    assert await repo.remove("does_not_exist") is False


async def test_list_active_ordered_by_added_at(repo):
    """AC-005: returns active channels ordered by added_at ascending."""
    await repo.add("first", title=None)
    await repo.add("second", title=None)
    await repo.add("third", title=None)

    channels = await repo.list_active()

    assert [c.username for c in channels] == ["first", "second", "third"]
    assert all(c.is_active == 1 for c in channels)


async def test_count_active(repo):
    """AC-006."""
    assert await repo.count_active() == 0
    await repo.add("first", title=None)
    await repo.add("second", title=None)
    assert await repo.count_active() == 2


async def test_username_normalisation_is_case_insensitive(repo):
    """AC-007: add('VC_RU') and remove('vc_ru') refer to the same channel."""
    await repo.add("VC_RU", title=None)

    channels = await repo.list_active()
    assert channels[0].username == "vc_ru"

    assert await repo.remove("vc_ru") is True
