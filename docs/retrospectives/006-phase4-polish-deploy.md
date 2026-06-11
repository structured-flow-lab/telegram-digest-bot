# Retrospective — 006 Phase 4: polish & deploy readiness

## What shipped

- `errors` table (migration) + `ErrorRepo.log(scope, message)`.
- `add_handler`, `remove_handler`, `channels_handler`, `_run_digest` now log
  unexpected exceptions to `errors` (in addition to existing console
  `logger.exception` + `GENERIC_ERROR` reply / `digest_runs.error_msg`).
- Removed unused `BOT_MODE`/`WEBHOOK_URL` from `app/config.py` and
  `.env.example` — bot is polling-only, locally and on Railway.
- `digest-bot/Dockerfile` + `.dockerignore` for Railway deploy (Python
  3.12-slim, `data/` mounted as a volume, not baked into the image).
- `docs/deployment.md` — local setup + Railway deploy guide (env vars,
  persistent volume, one-time Telethon login workaround for Railway).
- Rewrote root `README.md` to describe digest-bot as the actual product
  (was still describing the legacy Vite/React bootstrap).
- ADR 005 amended: polling chosen over webhook for both local and Railway.
- 100/102 tests passing (2 pre-existing `test_config.py` failures, see
  retro 003).

This completes Phase 4 per `docs/implementation-plan.md` and closes out the
Personal MVP per `docs/PRD.md` — all 9 success criteria verified in
[feature-006](../requirements/feature-006-phase4-polish-deploy.md#prd-checklist).

## Decision worth recording

- **Webhook mode dropped.** It was planned in ADR 005 for "Railway deploy",
  but Railway runs a persistent process (not serverless/FaaS), so polling
  works identically there. Webhook would have added a new dependency
  (`python-telegram-bot[webhooks]` → `tornado`) for zero benefit at this
  scale — confirmed with the project owner before implementing. **Lesson:**
  when a plan written early in the project (implementation-plan.md) bakes in
  an architectural choice, re-check it against the actual constraints of the
  chosen host before implementing — "deploy = webhook" was an unexamined
  assumption, not a requirement.

## Follow-ups (not done now)

- `tests/test_config.py` env-var-deletion failures remain (see retro 003,
  still unfixed — third feature in a row to note this; worth fixing soon so
  CI is fully green).
- No actual Railway deployment was performed in this session — the project
  owner needs to create a Railway account and follow
  `docs/deployment.md` themselves; Dockerfile/docs are untested against a
  real Railway build.
- Docker build was not verified locally (Docker not available in this
  environment) — worth a smoke build (`docker build .`) before relying on it
  for deploy.
