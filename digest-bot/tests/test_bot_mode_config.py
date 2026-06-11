"""Feature 005 — AC-001 – AC-004 — config.py BOT_MODE / webhook validation."""

import sys

import pytest


def test_invalid_bot_mode_raises(monkeypatch):
    """AC-001: BOT_MODE not in {polling, webhook} -> RuntimeError."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake:token")
    monkeypatch.setenv("OWNER_TELEGRAM_ID", "123")
    monkeypatch.setenv("BOT_MODE", "carrier-pigeon")
    sys.modules.pop("app.config", None)
    with pytest.raises(RuntimeError, match="BOT_MODE"):
        import app.config  # noqa: F401
    sys.modules.pop("app.config", None)


def test_webhook_mode_requires_webhook_url(monkeypatch):
    """AC-002: BOT_MODE=webhook with empty WEBHOOK_URL -> RuntimeError."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake:token")
    monkeypatch.setenv("OWNER_TELEGRAM_ID", "123")
    monkeypatch.setenv("BOT_MODE", "webhook")
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    sys.modules.pop("app.config", None)
    with pytest.raises(RuntimeError, match="WEBHOOK_URL"):
        import app.config  # noqa: F401
    sys.modules.pop("app.config", None)


def test_webhook_port_default(monkeypatch):
    """AC-003: WEBHOOK_PORT defaults to 8080."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake:token")
    monkeypatch.setenv("OWNER_TELEGRAM_ID", "123")
    monkeypatch.setenv("BOT_MODE", "polling")
    monkeypatch.delenv("WEBHOOK_PORT", raising=False)
    sys.modules.pop("app.config", None)
    import app.config as cfg
    assert cfg.WEBHOOK_PORT == 8080
    sys.modules.pop("app.config", None)


def test_polling_mode_allows_empty_webhook_url(monkeypatch):
    """AC-004: BOT_MODE=polling does not require WEBHOOK_URL."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake:token")
    monkeypatch.setenv("OWNER_TELEGRAM_ID", "123")
    monkeypatch.setenv("BOT_MODE", "polling")
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    sys.modules.pop("app.config", None)
    import app.config as cfg  # should not raise
    assert cfg.BOT_MODE == "polling"
    sys.modules.pop("app.config", None)
