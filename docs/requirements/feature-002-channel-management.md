# Feature 002 — Channel management (/add, /remove, /channels)

## Goal

Owner can add, remove, and list public Telegram channels the bot will read.
This is pure data-layer + handler logic — no Telethon, no network calls to Telegram
to verify channel existence yet (that arrives in Feature 003).

## User story

As the bot owner, I want to manage a list of public channels via `/add @channel`,
`/remove @channel`, and `/channels`, so the digest pipeline (Feature 004) knows what
to read.

## Scope

- `app/storage/repositories.py` — `ChannelRepo` (CRUD against the `channels` table
  created in migrations).
- `app/bot/handlers.py` — `/add`, `/remove`, `/channels` command handlers.
- `app/bot/messages.py` — new message templates for these commands.

## Acceptance criteria

### ChannelRepo (app/storage/repositories.py)

- AC-001: `add(username: str, title: str | None) -> Channel` inserts a row into
  `channels` and returns it. `username` is stored without a leading `@`.
- AC-002: `add()` raises `ChannelAlreadyExists` if the username (case-insensitive)
  is already present.
- AC-003: `add()` raises `ChannelLimitReached` if `count_active() >= MAX_CHANNELS`
  (from `config.MAX_CHANNELS`).
- AC-004: `remove(username: str) -> bool` deletes the channel row; returns `True`
  if a row was deleted, `False` if no matching channel existed.
- AC-005: `list_active() -> list[Channel]` returns all channels with `is_active = 1`,
  ordered by `added_at` ascending.
- AC-006: `count_active() -> int` returns the number of active channels.
- AC-007: Username normalisation is case-insensitive: `add("VC_RU")` and
  `remove("vc_ru")` refer to the same channel.

### Handlers (app/bot/handlers.py)

- AC-010: `/add @channel` with a valid, new username calls `ChannelRepo.add()` and
  replies with `messages.CHANNEL_ADDED.format(username=...)`.
- AC-011: `/add @channel` with no argument or malformed username (doesn't match
  `^@?[A-Za-z0-9_]{5,32}$`) replies with `messages.CHANNEL_INVALID_FORMAT`.
- AC-012: `/add @channel` for an already-added channel replies with
  `messages.CHANNEL_ALREADY_EXISTS.format(username=...)`.
- AC-013: `/add @channel` when the channel limit is reached replies with
  `messages.CHANNEL_LIMIT_REACHED.format(limit=config.MAX_CHANNELS)`.
- AC-014: `/remove @channel` for an existing channel calls `ChannelRepo.remove()`
  and replies with `messages.CHANNEL_REMOVED.format(username=...)`.
- AC-015: `/remove @channel` for a channel not in the list replies with
  `messages.CHANNEL_NOT_FOUND.format(username=...)`.
- AC-016: `/channels` with zero channels replies with `messages.CHANNELS_EMPTY`.
- AC-017: `/channels` with one or more channels replies with a formatted list,
  one `@username` per line, prefixed by `messages.CHANNELS_HEADER`.
- AC-018: All three handlers respect `owner_guard()` — non-owner messages produce
  no reply (consistent with Feature 001 behaviour).
- AC-019: Any unexpected exception inside a handler is caught, logged, and replies
  with `messages.GENERIC_ERROR` — the bot must not crash.

## Out of scope

- Verifying the channel actually exists / is public on Telegram (Feature 003,
  Telethon).
- Reading posts from the channel (Feature 003).
- `/digest` command (Feature 004).

## Notes

- `Channel` can be a small `NamedTuple` or `dataclass` mirroring the `channels`
  table columns (`id`, `username`, `title`, `added_at`, `is_active`).
- Reuse the existing `app/storage/db.get_connection()` context manager.
