# Feature 005 — Polish & deploy

## Goal

Make the bot resilient to unexpected errors, runnable in webhook mode, containerised, and
documented so it can be deployed to Railway (Phase 4 of the implementation plan).

## User story

As the bot owner, I want the bot to keep running and tell me what went wrong instead of
crashing on an unexpected error, and I want a documented, repeatable way to deploy it to
Railway in webhook mode.

## Scope

- `app/bot/error_handler.py` — global PTB error handler.
- `app/main.py` — register the error handler; support `BOT_MODE=webhook`.
- `app/config.py` — validate `BOT_MODE` and webhook-related settings.
- `digest-bot/Dockerfile`, `digest-bot/.dockerignore`.
- `digest-bot/README.md`.

## Acceptance criteria

### Config (app/config.py)

- AC-001: `config.py` raises `RuntimeError` at import time if `BOT_MODE` is not one of
  `"polling"` or `"webhook"`.
- AC-002: When `BOT_MODE == "webhook"`, `config.py` raises `RuntimeError` at import time if
  `WEBHOOK_URL` is empty.
- AC-003: `config.py` exposes `WEBHOOK_PORT: int` (env `WEBHOOK_PORT`, default `8080`).
- AC-004: When `BOT_MODE == "polling"`, `WEBHOOK_URL` may be empty — no error is raised.

### Global error handler (app/bot/error_handler.py)

- AC-010: `async def error_handler(update, context)` logs `context.error` (with traceback)
  via `logger.error(..., exc_info=context.error)`.
- AC-011: If `update` is an `Update` instance with a non-`None` `effective_message`, the
  handler best-effort sends `messages.GENERIC_ERROR` to that chat. Any exception raised while
  sending this message is caught and logged, never propagated.
- AC-012: If `update` is `None` or has no `effective_message` (e.g. an error from a job
  queue), the handler only logs — it does not attempt to send a message.

### main.py wiring

- AC-020: `main()` registers `error_handler` via
  `application.add_error_handler(error_handler)`.
- AC-021: When `config.BOT_MODE == "polling"`, `main()` calls `application.run_polling(...)`
  exactly as before (Feature 001 behaviour unchanged).
- AC-022: When `config.BOT_MODE == "webhook"`, `main()` calls `application.run_webhook(...)`
  with `listen="0.0.0.0"`, `port=config.WEBHOOK_PORT`, `url_path=config.TELEGRAM_BOT_TOKEN`,
  and `webhook_url=f"{config.WEBHOOK_URL}/{config.TELEGRAM_BOT_TOKEN}"`,
  `drop_pending_updates=True`.

### Dockerfile (digest-bot/Dockerfile)

- AC-030: `digest-bot/Dockerfile` exists, uses a `python:3.12-slim` base image, copies
  `requirements.txt` and runs `pip install --no-cache-dir -r requirements.txt` before copying
  the rest of the source (for layer caching).
- AC-031: The image's default command runs the bot: `CMD ["python", "app/main.py"]`, with
  `WORKDIR` set so `app/main.py`'s `sys.path` adjustment still resolves `app` as a package.
- AC-032: `digest-bot/.dockerignore` exists and excludes at least `data/`, `.env`,
  `__pycache__/`, `*.session`, and `tests/` from the build context.

### README (digest-bot/README.md)

- AC-040: `digest-bot/README.md` exists and documents:
  - prerequisites and required env vars (cross-referencing `.env.example`),
  - local setup: `pip install -r requirements.txt`, `python app/main.py` (polling mode),
  - one-time interactive Telethon login step (creates `data/telethon.session`),
  - Railway deployment: building from `Dockerfile`, setting `BOT_MODE=webhook` +
    `WEBHOOK_URL`, and attaching a persistent volume for `data/`.
- AC-041: `digest-bot/README.md` includes a checklist mapping each of the 9 MVP success
  criteria from `docs/PRD.md` to how it is satisfied / verified.

## Out of scope

- Automated CI/CD pipeline.
- Postgres migration, multi-user support, monetisation (per `docs/PRD.md` "Path to next MVP").

## Notes

- Keep `error_handler` independent of `owner_guard` — PTB invokes the global error handler for
  *any* update, including ones that never reached a command handler.
- `run_webhook`'s `url_path`/`webhook_url` use the bot token as a simple shared secret in the
  URL path, which is the standard `python-telegram-bot` pattern; do not log the full webhook
  URL (it contains the token).
