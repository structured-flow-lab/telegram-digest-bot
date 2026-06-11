"""Configuration — loaded from .env via python-dotenv."""

import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name!r} is not set")
    return value


# --- Telegram ---
TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_ID: int = int(os.getenv("TELEGRAM_API_ID") or "0")
TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH") or ""
OWNER_TELEGRAM_ID: int = int(_require("OWNER_TELEGRAM_ID"))

# --- Anthropic ---
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY") or ""

# --- Storage ---
DB_PATH: str = os.getenv("DB_PATH") or "data/digest_bot.sqlite"

# --- LLM ---
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER") or "claude"
LLM_MODEL: str = os.getenv("LLM_MODEL") or "claude-haiku-4-5-20251001"

# --- Bot mode ---
BOT_MODE: str = os.getenv("BOT_MODE") or "polling"
WEBHOOK_URL: str = os.getenv("WEBHOOK_URL") or ""

# --- Hard limits ---
MAX_DAYS: int = 30
MAX_CHANNELS: int = 20
MAX_POSTS_PER_DIGEST: int = 300
MAX_POSTS_PER_CHANNEL: int = 100
