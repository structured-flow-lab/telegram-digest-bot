"""Configuration — loaded from .env via python-dotenv."""

import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name!r} is not set")
    return value


def _require_int(name: str) -> int:
    value = _require(name)
    try:
        return int(value)
    except ValueError:
        raise RuntimeError(f"Environment variable {name!r} must be an integer, got {value!r}")


def _optional_int(name: str, default: int = 0) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        raise RuntimeError(f"Environment variable {name!r} must be an integer, got {value!r}")


# --- Telegram ---
TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_ID: int = _optional_int("TELEGRAM_API_ID")
TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH") or ""
OWNER_TELEGRAM_ID: int = _require_int("OWNER_TELEGRAM_ID")

# --- Anthropic ---
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY") or ""

# --- Storage ---
DB_PATH: str = os.getenv("DB_PATH") or "data/digest_bot.sqlite"

# --- LLM ---
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER") or "claude"
LLM_MODEL: str = os.getenv("LLM_MODEL") or "claude-haiku-4-5-20251001"

# --- Hard limits ---
MAX_DAYS: int = 30
MAX_CHANNELS: int = 20
MAX_POSTS_PER_DIGEST: int = 300
MAX_POSTS_PER_CHANNEL: int = 100
