"""Feature 003 — AC-001 – AC-003 — Telethon client lifecycle (app/reader/telethon_client.py)."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _reset_telethon_client_module():
    """Drop cached `app.config` / `app.reader.telethon_client` so the next import is fresh.

    Popping from sys.modules alone is not enough: `app.reader` keeps a
    `telethon_client` attribute pointing at the old module object, so
    `from app.reader import telethon_client` would silently resolve to the
    stale module via attribute lookup instead of re-importing — which matters
    here because the stale module already has `telethon.TelegramClient` bound
    from before `telethon.TelegramClient` gets patched.
    """
    import app
    import app.reader as appreader

    sys.modules.pop("app.config", None)
    sys.modules.pop("app.reader.telethon_client", None)
    if hasattr(app, "config"):
        delattr(app, "config")
    if hasattr(appreader, "telethon_client"):
        delattr(appreader, "telethon_client")


@pytest.fixture(autouse=True)
def ensure_config(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake:token")
    monkeypatch.setenv("OWNER_TELEGRAM_ID", "999")
    _reset_telethon_client_module()
    yield
    _reset_telethon_client_module()


async def test_get_client_returns_singleton(monkeypatch):
    """AC-001: get_client() returns a singleton TelegramClient with session in data/."""
    monkeypatch.setenv("TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("TELEGRAM_API_HASH", "abc123")
    _reset_telethon_client_module()

    fake_client = MagicMock()
    with patch("telethon.TelegramClient", return_value=fake_client) as mock_cls:
        from app.reader import telethon_client

        client1 = telethon_client.get_client()
        client2 = telethon_client.get_client()

    assert client1 is client2
    mock_cls.assert_called_once()
    args, kwargs = mock_cls.call_args
    session_arg = args[0] if args else kwargs.get("session")
    assert "telethon" in str(session_arg)
    assert "data" in str(session_arg)


async def test_get_client_raises_without_api_credentials(monkeypatch):
    """AC-002: raises RuntimeError if TELEGRAM_API_ID / TELEGRAM_API_HASH unset."""
    monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)
    _reset_telethon_client_module()

    from app.reader import telethon_client

    with pytest.raises(RuntimeError):
        telethon_client.get_client()


async def test_ensure_connected_is_idempotent():
    """AC-003: ensure_connected() connects lazily and is safe to call repeatedly."""
    _reset_telethon_client_module()
    from app.reader import telethon_client

    client = MagicMock()
    client.is_connected = MagicMock(return_value=False)
    client.connect = AsyncMock()

    await telethon_client.ensure_connected(client)
    client.connect.assert_awaited_once()

    client.is_connected.return_value = True
    await telethon_client.ensure_connected(client)
    # still only called once — already connected, no-op the second time
    client.connect.assert_awaited_once()
