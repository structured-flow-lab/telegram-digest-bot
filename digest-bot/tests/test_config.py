"""AC-001, AC-002, AC-003 — config loading."""

import importlib
import os
import sys
import pytest


def _reload_config(env: dict):
    """Import config with a controlled environment."""
    # Remove cached module so re-import re-executes module-level code.
    sys.modules.pop("app.config", None)
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        import app.config as cfg
        return cfg
    finally:
        # Restore env
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        sys.modules.pop("app.config", None)


def test_raises_without_bot_token(monkeypatch):
    """AC-001: missing TELEGRAM_BOT_TOKEN raises RuntimeError."""
    # config.py calls load_dotenv() on import, which would otherwise refill
    # TELEGRAM_BOT_TOKEN from digest-bot/.env and mask the missing-var case.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("OWNER_TELEGRAM_ID", "123")
    sys.modules.pop("app.config", None)
    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        import app.config  # noqa: F401
    sys.modules.pop("app.config", None)


def test_raises_without_owner_id(monkeypatch):
    """AC-002: missing OWNER_TELEGRAM_ID raises RuntimeError."""
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake:token")
    monkeypatch.delenv("OWNER_TELEGRAM_ID", raising=False)
    sys.modules.pop("app.config", None)
    with pytest.raises(RuntimeError, match="OWNER_TELEGRAM_ID"):
        import app.config  # noqa: F401
    sys.modules.pop("app.config", None)


def test_hard_limits(monkeypatch):
    """AC-003: hard limits are fixed constants."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake:token")
    monkeypatch.setenv("OWNER_TELEGRAM_ID", "123")
    sys.modules.pop("app.config", None)
    import app.config as cfg
    assert cfg.MAX_DAYS == 30
    assert cfg.MAX_CHANNELS == 20
    assert cfg.MAX_POSTS_PER_DIGEST == 300
    assert cfg.MAX_POSTS_PER_CHANNEL == 100
    sys.modules.pop("app.config", None)
