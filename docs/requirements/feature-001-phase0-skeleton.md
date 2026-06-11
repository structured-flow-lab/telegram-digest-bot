# Feature 001 — Phase 0 skeleton

## Goal

Establish a working Python bot skeleton: config loading, SQLite migrations, owner-guard
middleware, and basic /start + /help command handlers.

No Telethon, no LLM calls. Just the infrastructure that every later phase builds on.

## Acceptance criteria

### Config (app/config.py)

- AC-001: Raises `RuntimeError` at import time if `TELEGRAM_BOT_TOKEN` is not set.
- AC-002: Raises `RuntimeError` at import time if `OWNER_TELEGRAM_ID` is not set.
- AC-003: Hard limits are fixed constants: `MAX_DAYS=30`, `MAX_CHANNELS=20`,
  `MAX_POSTS_PER_DIGEST=300`, `MAX_POSTS_PER_CHANNEL=100`.

### Migrations (app/storage/migrations.py)

- AC-010: `run_migrations()` creates table `channels` with columns
  `id, username, title, added_at, is_active`.
- AC-011: `run_migrations()` creates table `posts_cache` with columns
  `id, channel_id, telegram_msg_id, posted_at, text, url, fetched_at`.
- AC-012: `run_migrations()` creates table `digest_runs` with columns
  `id, started_at, finished_at, days, channel_filter, posts_fetched, posts_included,
  status, error_msg`.
- AC-013: `run_migrations()` creates table `llm_usage` with columns
  `id, digest_run_id, provider, model, prompt_version, input_tokens,
  output_tokens, called_at`.
- AC-014: Calling `run_migrations()` twice on the same DB does not raise an error
  (idempotent — CREATE TABLE IF NOT EXISTS).

### Owner guard (app/bot/handlers.py)

- AC-020: `owner_guard()` returns `True` when `update.effective_user.id` equals
  `OWNER_TELEGRAM_ID`.
- AC-021: `owner_guard()` returns `False` when the user id does not match.
- AC-022: `owner_guard()` returns `False` when `update.effective_user` is `None`.

### Messages (app/bot/messages.py)

- AC-030: `messages.START` is a non-empty string.
- AC-031: `messages.HELP` is a non-empty string containing "/help".

## Out of scope

- Actual Telegram network calls.
- Telethon, LLM, webhook setup.
