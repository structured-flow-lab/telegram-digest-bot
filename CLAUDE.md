# CLAUDE.md — telegram-digest-bot

## Project description
A web application that reads selected public Telegram channels and generates a short AI digest
for a requested time period, viewable in a browser by end users.

---

## Repository layout

```
telegram-digest-bot/          ← repo root (git, governance)
  CLAUDE.md                   ← entry point for Claude (this file)
  README.md                   ← entry point for humans
  package.json                ← root pass-through scripts
  .gitignore  .editorconfig  .nvmrc  .env.example
  docs/
    requirements/             ← feature specs (feature-NNN-*.md)
    decisions/                ← ADRs (NNN-*.md)
    retrospectives/           ← retros after every feature
    constraints.md
  app/                        ← legacy Vite + React + TS bootstrap (superseded, see ADR 002-005)
    src/
    vite.config.ts
    vitest.config.ts
    package.json
    ...
  digest-bot/                 ← Python Telegram bot (the actual product, per ADR 002-005)
    app/
      bot/                    ← handlers, message text
      config.py
      digest/  llm/  reader/  storage/
    tests/
    requirements.txt  dev-requirements.txt  pytest.ini
    .env.example  data/
```

Governance files (`CLAUDE.md`, `README.md`, `docs/**`) live at the repo root — never inside `app/` or `digest-bot/`.
The product is the Python bot under `digest-bot/` (ADRs 002-005). The root `app/` directory is the
original Vite/React bootstrap from feature 001-hello-world and is not actively developed; do not
add new product code there.

---

## Dev server

From repo root:
```
npm run dev  →  http://127.0.0.1:5173/
```
Port is recorded in `.dev-port` (defaults 5173). Always read current port from `.dev-port`.

---

## Common commands (all from repo root)

| Command            | What it does                        |
|--------------------|-------------------------------------|
| `npm run dev`      | Start Vite dev server               |
| `npm run build`    | Type-check + production build       |
| `npm run preview`  | Serve the production build locally  |
| `npm run test`     | Run tests in watch mode             |
| `npm run test:run` | Run tests once (CI mode)            |
| `npm run lint`     | ESLint                              |
| `npm run format`   | Prettier                            |
| `npm run setup`    | Install app/ dependencies           |

---

## Critical files

- `app/vite.config.ts` — Vite config, port settings, path alias `@/`
- `app/vitest.config.ts` — Vitest config (environment: node)
- `docs/constraints.md` — what NOT to do; read before proposing anything

---

## How to work in this repo

**Working agreement**

1. No code without a spec. Every feature begins as a file under `docs/requirements/` and a failing test under `app/src/**/*.spec.ts(x)`.
2. No architectural choice without an ADR under `docs/decisions/`.
3. Read `docs/constraints.md` before proposing anything new. Surface conflicts, don't silently comply.
4. The loop is: spec → failing test → minimal code → green test → commit. One concern per commit.
5. Logic in pure modules, rendering in components. Specs target the logic. Add a DOM-testing layer (e.g. React Testing Library) only via an ADR when a real need appears.
6. When in doubt, ask. Use AskUserQuestion rather than guessing requirements.
7. Keep `CLAUDE.md`'s "Current state" section updated after every merged change.
8. Dev server lives at `http://127.0.0.1:<DEV_PORT>/` where `DEV_PORT` is recorded in `.dev-port` (defaults to 5173). Always read the current port from `.dev-port` instead of hardcoding 5173. `strictPort: true` is set so Vite never silently drifts.
9. **Retrospective after every feature.** Once a feature is green and committed, write `docs/retrospectives/NNN-<slug>.md`. If the retro proposes a change, edit `CLAUDE.md` in the same session. Commit as `chore(retro): NNN-<slug>`.
10. **Layout discipline.** Governance files live at repo root, never inside `app/` or `digest-bot/`. Python product code lives inside `digest-bot/app/`, never at repo root.
11. **Conventional Commits.** Format: `<type>(<scope>): <subject>`. Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`, `style`.
12. **CLAUDE.md ≤ ~200 lines.** It is a router, not an encyclopedia. Route detail into linked docs.

---

## Escalation rules

Stop and ask via AskUserQuestion when:
- The same test has failed 3 times with different fixes (you're guessing — get more context).
- A request conflicts with `docs/constraints.md` or a rule in the "Rules" section of `CLAUDE.md`.
- A new runtime dependency is needed (ask + add an ADR before installing).
- `:5173` or `:4173` is taken (fix the conflict, do not let Vite drift to another port).
- This change would push `CLAUDE.md` past ~200 lines (route detail into a linked doc first).
- Acceptance criteria in a `docs/requirements/feature-*.md` are ambiguous or contradict each other.

---

## Rules

**TypeScript strict:** Do NOT disable `strict`, `noImplicitAny`, `strictNullChecks`, or
`noUncheckedIndexedAccess` in any `tsconfig*.json`. Narrow the type or guard the value —
never loosen the config.

**Pure modules:** Business logic lives in pure modules under `app/src/`. React components only
render — no branching/transform logic. Extract any non-trivial computation into a pure module
and spec it before wiring it in.

**Spec first:** Every new module starts with a failing `*.spec.ts(x)` test. Show the red
output, then write the minimum code to turn it green, then commit.

---

## Docs index

- [docs/PRD.md](docs/PRD.md)
- [docs/implementation-plan.md](docs/implementation-plan.md)
- [docs/requirements/overview.md](docs/requirements/overview.md)
- [docs/decisions/001-agent-structure.md](docs/decisions/001-agent-structure.md) — root vs app/ layout
- [docs/decisions/002-llm-abstraction.md](docs/decisions/002-llm-abstraction.md) — Protocol + factory
- [docs/decisions/003-sqlite-storage.md](docs/decisions/003-sqlite-storage.md) — SQLite для Personal MVP
- [docs/decisions/004-telethon-channel-reader.md](docs/decisions/004-telethon-channel-reader.md) — Telethon vs Bot API
- [docs/decisions/005-bot-framework-and-hosting.md](docs/decisions/005-bot-framework-and-hosting.md) — python-telegram-bot + Railway
- [docs/deployment.md](docs/deployment.md) — local setup + Railway deploy (polling)
- [docs/constraints.md](docs/constraints.md)
- [docs/retrospectives/](docs/retrospectives/) ← populated after each feature

---

## Current state

Phases 0–3 of the `digest-bot/` Python bot are done: env-based config, async SQLite migrations,
owner-only access guard, `/start /help /add /remove /channels`, Telethon channel reader + posts
cache, and the full digest pipeline (`app/llm/`, `app/digest/`, `app/prompts/digest_v1.md`,
`app/prompts/digest_v2.md`, `DigestRunRepo`/`LLMUsageRepo`) wired into `/digest <days>` and
`/digest @channel <days>`. Per feature 005, `/digest` now sends one table-of-contents-style
message per channel (linked item titles + optional notes, forced Russian output, via
`digest_v2.md`/`DigestItem`/`format_channel_digest`), reports per-channel fetch errors inline
without aborting the run, and acknowledges the command with a 👍 reaction instead of a status
message. Per feature 006 (Phase 4), unexpected errors are persisted to an `errors` table
(`ErrorRepo`) in addition to console logging, the bot runs polling-only (no webhook —
`BOT_MODE`/`WEBHOOK_URL` removed, see amended ADR 005), and `digest-bot/Dockerfile` +
[docs/deployment.md](docs/deployment.md) cover Railway deploy with a persistent `data/`
volume. 100/102 tests passing (2 pre-existing `test_config.py` failures, see retro 003).
Bot runs locally via `python app/main.py` (Telethon session requires one-time
`scripts/telethon_login.py`). All 9 PRD success criteria are met (see feature-006 checklist).
The root `app/` Vite/React bootstrap from feature 001 still exists but is not the active product.

---

## Self-improvement log

- [001-hello-world](docs/retrospectives/001-hello-world.md) — bootstrap retro; nc shim on Windows, eslint-plugin-react ESLint 10 incompatibility recorded.
- [002-channel-management-and-reader](docs/retrospectives/002-channel-management-and-reader.md) — PR description must say upfront if it bundles spec+test+implementation (don't claim "tests only"); mocked `iter_messages` hid an `offset_date`/`reverse` bug.
- [003-digest-pipeline](docs/retrospectives/003-digest-pipeline.md) — `asyncio.run()` before `run_polling()` breaks on Python 3.12, use `post_init`; Telethon first-run login needs a manual interactive script; existing `.env` broke 2 `test_config.py` env-deletion tests (follow-up needed).
- [005-digest-toc-per-channel](docs/retrospectives/005-digest-toc-per-channel.md) — when a prompt asks the LLM for "1+ items", the formatter must still handle an empty list gracefully (don't assume the prompt constraint is enforced); `_format_item` was indexing `urls[0]` unguarded and could crash the whole `/digest` run.
- [006-phase4-polish-deploy](docs/retrospectives/006-phase4-polish-deploy.md) — re-check early architectural plans (webhook for "deploy") against the actual host's constraints before implementing; Railway is a persistent process, so polling deploys fine and webhook was dropped.
