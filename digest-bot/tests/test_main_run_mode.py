"""Feature 005 — AC-020 – AC-022 — main.py error handler + run-mode wiring."""

import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def ensure_config(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake:token")
    monkeypatch.setenv("OWNER_TELEGRAM_ID", "999")
    sys.modules.pop("app.config", None)
    sys.modules.pop("app.main", None)
    yield
    sys.modules.pop("app.config", None)
    sys.modules.pop("app.main", None)


def _fake_application():
    application = MagicMock()
    builder = MagicMock()
    builder.token.return_value = builder
    builder.build.return_value = application
    return application, builder


def _run_main(monkeypatch):
    """Import app.main fresh and run main() with Application/asyncio mocked out."""
    sys.modules.pop("app.main", None)
    import app.main as main_module

    application, builder = _fake_application()

    fake_application_cls = MagicMock()
    fake_application_cls.builder.return_value = builder

    monkeypatch.setattr(main_module, "Application", fake_application_cls)
    monkeypatch.setattr(main_module, "asyncio", MagicMock())

    main_module.main()
    return main_module, application


def test_main_registers_error_handler(monkeypatch):
    """AC-020: main() registers app.bot.error_handler.error_handler."""
    monkeypatch.setenv("BOT_MODE", "polling")
    sys.modules.pop("app.config", None)

    main_module, application = _run_main(monkeypatch)

    application.add_error_handler.assert_called_once()
    from app.bot.error_handler import error_handler

    assert application.add_error_handler.call_args.args[0] is error_handler


def test_main_polling_mode_calls_run_polling(monkeypatch):
    """AC-021: BOT_MODE=polling -> application.run_polling(...)."""
    monkeypatch.setenv("BOT_MODE", "polling")
    sys.modules.pop("app.config", None)

    _, application = _run_main(monkeypatch)

    application.run_polling.assert_called_once()
    application.run_webhook.assert_not_called()


def test_main_webhook_mode_calls_run_webhook(monkeypatch):
    """AC-022: BOT_MODE=webhook -> application.run_webhook(listen, port, url_path, webhook_url)."""
    monkeypatch.setenv("BOT_MODE", "webhook")
    monkeypatch.setenv("WEBHOOK_URL", "https://example.up.railway.app")
    sys.modules.pop("app.config", None)

    main_module, application = _run_main(monkeypatch)

    application.run_polling.assert_not_called()
    application.run_webhook.assert_called_once()
    kwargs = application.run_webhook.call_args.kwargs
    assert kwargs["listen"] == "0.0.0.0"
    assert kwargs["port"] == main_module.config.WEBHOOK_PORT
    assert kwargs["url_path"] == main_module.config.TELEGRAM_BOT_TOKEN
    assert kwargs["webhook_url"] == f"https://example.up.railway.app/{main_module.config.TELEGRAM_BOT_TOKEN}"
    assert kwargs["drop_pending_updates"] is True
