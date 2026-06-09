# PRD — Telegram Content Digest Bot

## Problem

Information overload in Telegram: people subscribe to dozens of channels but have no time to
read everything. There is no native way to get a structured summary of what happened across
multiple channels for a given period.

**Who it's for (Personal MVP):** a single owner — a power Telegram user who follows 5–20
public channels and wants a quick thematic digest on demand, not a full feed.

**Who it's for (next MVP):** any Telegram user who wants the same, with per-user channel lists,
usage limits, and optional paid plans.

---

## Core user scenarios

| # | Scenario | Entry point |
|---|----------|-------------|
| 1 | Add a public channel to watch | `/add @channel` |
| 2 | Remove a channel | `/remove @channel` |
| 3 | View saved channels | `/channels` |
| 4 | Generate a digest across all channels for N days | `/digest <days>` |
| 5 | Generate a digest for one channel for N days | `/digest @channel <days>` |
| 6 | Get help / command list | `/start`, `/help` |

**Digest output contract:**
- Posts are grouped into 3–7 thematic clusters, not listed one by one.
- Each cluster has a 2–4 sentence summary and links to the original posts.
- Header shows: channels included, total posts read, posts included in digest.

---

## In scope — Personal MVP

- Single-owner bot (responds only to `OWNER_TELEGRAM_ID`).
- Read public Telegram channels via Telethon.
- SQLite storage: channels, post cache, digest runs, LLM usage, errors.
- Claude API for thematic grouping and summarisation.
- Post cache — avoid re-fetching already-read messages.
- Skip posts without text (photo/video-only, too short, service messages).
- Technical limits in config: max 30 days, 20 channels, 300 posts/digest, 100 posts/channel.
- Safe error handling: unavailable channel, empty result, Telegram API error, LLM error.
- Prompt stored separately and versioned (`prompts/digest_v1.md`).
- Architecture ready for multi-user expansion (no user ID hard-coded in logic).

---

## Out of scope — Personal MVP

- Multi-user mode.
- Monetisation, Telegram Stars, paid plans, usage limits per user.
- Scheduled / automatic digest.
- Private channels.
- Comments / discussion group summary.
- Telegram Mini App.
- Postgres or any external database.
- Pinned message as data store.

---

## MVP success criteria

The Personal MVP is **done** when all of the following are true:

1. Bot starts locally and responds only to the owner.
2. Owner can add and remove a public channel; errors return a clear message.
3. `/channels` shows the current list.
4. `/digest <days>` produces a grouped thematic digest with original-post links.
5. `/digest @channel <days>` does the same for a single channel.
6. Posts are cached in SQLite; a second digest request for the same period does not re-fetch.
7. Any Telegram API, LLM, or DB error returns a user-friendly message and does not crash the bot.
8. LLM usage (model, tokens) is recorded per digest run.
9. Code structure matches the agreed module layout so a second developer can add multi-user
   support without rewriting business logic.

---

## Path to next MVP (not in scope now, noted for architecture)

| Addition | What needs to change |
|----------|----------------------|
| Multi-user | Add `users` + `user_channels` tables; pass `user_id` through all layers |
| Usage limits | Add limits table; check in handlers before running digest |
| Scheduled digest | Add a scheduler layer; reuse existing digest pipeline |
| Comments summary | Add a Telethon fetch step for discussion groups |
| Monetisation | Add `subscriptions` table; gate features by plan in handlers |
| Postgres | Swap SQLite adapter in `storage/db.py`; no other layer changes |
