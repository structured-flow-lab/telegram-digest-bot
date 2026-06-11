"""Telethon client lifecycle (singleton, lazy connection)."""

import os

from telethon import TelegramClient

SESSION_PATH = "data/telethon.session"

_client: TelegramClient | None = None


def _api_id() -> int:
    raw = os.getenv("TELEGRAM_API_ID")
    try:
        return int(raw) if raw else 0
    except ValueError:
        return 0


def _api_hash() -> str:
    return os.getenv("TELEGRAM_API_HASH") or ""


def get_client() -> TelegramClient:
    """Return a singleton TelegramClient configured from environment.

    Raises RuntimeError if TELEGRAM_API_ID or TELEGRAM_API_HASH is unset/zero/empty.
    """
    global _client

    api_id = _api_id()
    api_hash = _api_hash()

    if not api_id or not api_hash:
        raise RuntimeError(
            "TELEGRAM_API_ID and TELEGRAM_API_HASH must be set to use the Telethon client"
        )

    if _client is not None:
        return _client

    _client = TelegramClient(SESSION_PATH, api_id, api_hash)
    return _client


async def ensure_connected(client: TelegramClient) -> None:
    """Connect the client if it is not already connected (idempotent)."""
    if not client.is_connected():
        await client.connect()
