"""AC-020 – AC-022 — owner_guard logic."""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch


def _make_update(user_id):
    """Build a minimal fake Update with effective_user.id = user_id."""
    update = MagicMock()
    if user_id is None:
        update.effective_user = None
    else:
        update.effective_user = MagicMock()
        update.effective_user.id = user_id
    return update


@pytest.fixture(autouse=True)
def ensure_config(monkeypatch):
    """Ensure app.config is importable (minimal valid env)."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake:token")
    monkeypatch.setenv("OWNER_TELEGRAM_ID", "999")
    sys.modules.pop("app.config", None)
    sys.modules.pop("app.bot.handlers", None)
    yield
    sys.modules.pop("app.config", None)
    sys.modules.pop("app.bot.handlers", None)


async def test_owner_guard_owner():
    """AC-020: returns True for the owner."""
    from app.bot import handlers
    with patch.object(handlers.config, "OWNER_TELEGRAM_ID", 42):
        result = await handlers.owner_guard(_make_update(42), MagicMock())
    assert result is True


async def test_owner_guard_stranger():
    """AC-021: returns False for a different user."""
    from app.bot import handlers
    with patch.object(handlers.config, "OWNER_TELEGRAM_ID", 42):
        result = await handlers.owner_guard(_make_update(999), MagicMock())
    assert result is False


async def test_owner_guard_no_user():
    """AC-022: returns False when effective_user is None."""
    from app.bot import handlers
    with patch.object(handlers.config, "OWNER_TELEGRAM_ID", 42):
        result = await handlers.owner_guard(_make_update(None), MagicMock())
    assert result is False
