# Feature 006 — Phase 4: polish & deploy readiness

## Background

Phases 0–3 are done (env config, SQLite storage, channel management, Telethon
reader, digest pipeline with per-channel TOC output). Per
`docs/implementation-plan.md` Phase 4 ("Полировка и деплой"), the remaining
work before the Personal MVP is "done" per `docs/PRD.md` is:

- Persist unexpected errors (table + console), not just log them.
- Make the project deployable on Railway.
- Document local setup and deployment.
- Verify the 9 PRD success criteria explicitly.

## Decision: polling, not webhook

`docs/decisions/005-bot-framework-and-hosting.md` originally proposed
`BOT_MODE=webhook` for Railway. Railway runs the app as a persistent
process (not serverless), so polling works there exactly as it does locally
— no public HTTPS endpoint is required. Webhook mode would add a new runtime
dependency (`python-telegram-bot[webhooks]` → `tornado`) for no operational
benefit at this scale. **Decision (confirmed with the project owner): keep
polling for both local and Railway.** `BOT_MODE`/`WEBHOOK_URL` config values
are removed; `main.py` always runs `run_polling()`. ADR 005 is amended
accordingly rather than superseded (framework + hosting choice unchanged).

## Goal

The bot can be deployed to Railway via Docker, persists unexpected errors to
SQLite for later inspection, and the repo has a deployment guide. All 9 PRD
success criteria are verified and recorded.

## Scope

- `app/storage/migrations.py` — new `errors` table.
- `app/storage/repositories.py` — `ErrorRepo.log(scope, message)`.
- `app/bot/handlers.py` — every existing `except Exception` / digest-run
  failure branch also calls `ErrorRepo.log(...)`.
- `app/config.py` — drop unused `BOT_MODE` / `WEBHOOK_URL`.
- `digest-bot/Dockerfile`, `digest-bot/.dockerignore` — container image for
  Railway.
- `docs/deployment.md` — local run + Railway deploy steps, persistent volume
  for `data/`.
- `README.md` (root) — updated to describe the actual product (digest-bot),
  link to `docs/deployment.md`.
- `digest-bot/.env.example` — drop `BOT_MODE`/`WEBHOOK_URL`.

## Out of scope

- Webhook mode (see decision above).
- A `/errors`-style admin command to read the table from Telegram — the table
  is for manual SQLite inspection only.
- Postgres, multi-user, scheduled digests (per PRD "Path to next MVP").

## Acceptance criteria

### Error logging (AC-200 – AC-204)

- AC-200: `errors` table: `id`, `occurred_at` (default `datetime('now')`),
  `scope` (TEXT, e.g. `"add_channel"`, `"digest_run"`), `message` (TEXT).
- AC-201: `run_migrations()` creates the `errors` table; idempotent like the
  existing tables.
- AC-202: `ErrorRepo(conn).log(scope: str, message: str) -> None` inserts a
  row and commits.
- AC-203: Each `except Exception` branch in `add_handler`, `remove_handler`,
  `channels_handler` calls `ErrorRepo(conn).log(...)` in addition to the
  existing `logger.exception(...)` and user-facing `GENERIC_ERROR` reply.
- AC-204: The `except Exception` branch in `_run_digest` calls
  `ErrorRepo(conn).log("digest_run", str(exc))` in addition to
  `run_repo.fail(...)` and `logger.exception(...)`.

### Config cleanup (AC-210)

- AC-210: `BOT_MODE` and `WEBHOOK_URL` are removed from `app/config.py` and
  `digest-bot/.env.example`. `main.py` calls `run_polling()` unconditionally
  (no behaviour change — it already did this).

### Deploy artifacts (AC-220 – AC-222)

- AC-220: `digest-bot/Dockerfile` — Python 3.12-slim base, installs
  `requirements.txt`, copies `app/` and `prompts/`, runs
  `python app/main.py`. `data/` is not baked into the image (mounted as a
  volume at runtime).
- AC-221: `digest-bot/.dockerignore` excludes `data/`, `.env`,
  `__pycache__/`, `tests/`.
- AC-222: `docs/deployment.md` documents: local setup (`.env`, Telethon
  login script, `python app/main.py`), and Railway deploy (Dockerfile
  build, env vars to set, persistent volume mounted at `data/` for the
  SQLite file + Telethon session).

### PRD verification (AC-230)

- AC-230: `docs/requirements/feature-006-phase4-polish-deploy.md` (this file)
  records a checklist mapping each of the 9 PRD success criteria to evidence
  (test, manual run, or doc) — see "PRD checklist" below.

## PRD checklist

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Bot starts locally, responds only to owner | ✅ Phase 0, `owner_guard` |
| 2 | Add/remove a public channel, clear errors | ✅ Phase 1, `test_channel_handlers.py` |
| 3 | `/channels` shows current list | ✅ Phase 1 |
| 4 | `/digest <days>` grouped digest with links | ✅ Phase 3/5 (per-channel TOC) |
| 5 | `/digest @channel <days>` same, single channel | ✅ Phase 3/5 |
| 6 | Posts cached in SQLite, no re-fetch on repeat | ✅ Phase 2, `PostsCacheRepo` |
| 7 | API/LLM/DB errors → friendly message, no crash | ✅ + this feature (persisted to `errors`) |
| 8 | LLM usage recorded per digest run | ✅ Phase 3, `LLMUsageRepo` |
| 9 | Module layout ready for multi-user extension | ✅ ADRs 001–005 |
