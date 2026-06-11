# Feature 003 — Telethon channel reader + posts cache

## Goal

Read posts from public Telegram channels via Telethon and cache them in
`posts_cache` so repeated digest requests for an overlapping period don't
re-fetch already-seen messages.

## User story

As the bot owner, when I `/add @channel`, the bot verifies the channel is public
and readable. When a digest is generated (Feature 004), posts are pulled from the
cache first and only missing/newer posts are fetched from Telegram.

## Scope

- `app/reader/telethon_client.py` — Telethon client lifecycle (init, session file,
  shutdown).
- `app/reader/posts.py` — `fetch_posts(channel_username, since)` and channel
  validation.
- `app/storage/repositories.py` — `PostsCacheRepo`.
- `app/bot/handlers.py` — wire channel validation into `/add` (extends Feature 002).

## Acceptance criteria

### Telethon client (app/reader/telethon_client.py)

- AC-001: `get_client() -> TelegramClient` returns a singleton `TelegramClient`
  configured with `config.TELEGRAM_API_ID` / `config.TELEGRAM_API_HASH` and a
  session file at `data/telethon.session`.
- AC-002: `get_client()` raises `RuntimeError` if `TELEGRAM_API_ID` or
  `TELEGRAM_API_HASH` is unset/zero (config already loads them as optional —
  this feature makes them required at call time, not at import time).
- AC-003: The client connects lazily — `get_client()` does not connect; a
  separate `async def ensure_connected(client)` does, and is idempotent
  (safe to call repeatedly).

### Channel validation (app/reader/posts.py)

- AC-010: `async def validate_channel(username: str) -> ChannelInfo` resolves the
  entity via Telethon and returns `ChannelInfo(username, title, is_public)`.
- AC-011: `validate_channel()` raises `ChannelNotFound` if Telethon cannot resolve
  the username (e.g. `UsernameNotOccupiedError`, `UsernameInvalidError`).
- AC-012: `validate_channel()` raises `ChannelNotPublic` if the resolved entity is
  a private channel/chat (no public username) or not a broadcast channel.

### Post fetching (app/reader/posts.py)

- AC-020: `async def fetch_posts(username: str, since: datetime, limit: int) -> list[Post]`
  returns posts newer than `since`, oldest-to-newest, capped at `limit`
  (`config.MAX_POSTS_PER_CHANNEL`).
- AC-021: `Post` carries: `telegram_msg_id`, `posted_at` (UTC datetime), `text`,
  `url` (`https://t.me/{username}/{msg_id}`), `views` (optional).
- AC-022: Posts with empty/`None` `.message` text are skipped (not returned) —
  satisfies PRD "skip posts without text".
- AC-023: On `FloodWaitError`, `fetch_posts()` raises `ChannelFetchError` with the
  wait time included in the message — caller decides whether to retry; this
  function does not sleep/retry internally.
- AC-024: On any other Telethon/RPC error, `fetch_posts()` raises
  `ChannelFetchError` wrapping the original exception.

### PostsCacheRepo (app/storage/repositories.py)

- AC-030: `async def upsert_posts(channel_id: int, posts: list[Post]) -> int`
  inserts posts into `posts_cache`, ignoring duplicates on
  `(channel_id, telegram_msg_id)` (`INSERT OR IGNORE`); returns count of newly
  inserted rows.
- AC-031: `async def latest_cached_at(channel_id: int) -> datetime | None` returns
  the max `posted_at` for the channel, or `None` if the cache is empty for that
  channel.
- AC-032: `async def get_cached_since(channel_id: int, since: datetime, limit: int) -> list[CachedPost]`
  returns cached posts with `posted_at >= since`, oldest-to-newest, capped at
  `limit`.

### Wiring into /add (app/bot/handlers.py)

- AC-040: `/add @channel` calls `validate_channel()` before `ChannelRepo.add()`.
- AC-041: If `validate_channel()` raises `ChannelNotFound`, reply with
  `messages.CHANNEL_NOT_FOUND_ON_TELEGRAM.format(username=...)` and do not insert
  a row.
- AC-042: If `validate_channel()` raises `ChannelNotPublic`, reply with
  `messages.CHANNEL_NOT_PUBLIC.format(username=...)`.
- AC-043: On success, the channel's `title` (from `ChannelInfo`) is stored, not
  left `NULL`.

## Out of scope

- Digest generation / LLM calls (Feature 004).
- Reading comments / discussion groups.
- Automatic retry/backoff loops for `FloodWaitError` (logged and surfaced as an
  error to the caller for now).

## Notes

- Tests for Telethon-dependent code must mock `TelegramClient` — no real network
  calls in the test suite (per `docs/constraints.md`, no new runtime deps without
  an ADR; `unittest.mock` / `pytest`'s built-in mocking is sufficient).
- Telethon session file (`data/telethon.session`) requires one-time interactive
  login — document this in README as a manual setup step, not part of automated
  tests.
