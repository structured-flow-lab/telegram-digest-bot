# Constraints — telegram-digest-bot

## From project definition (Step 1)

- **No mobile app.** Web browser only.
- **No real-time chat.** Read-only digest view; no two-way messaging with Telegram.

## Baseline engineering constraints

- **No unscoped refactors.** Every change must be tied to a spec or bug fix.
- **No new runtime dependencies without an ADR.** Propose → ADR → install.
- **No code without a spec.** Every module starts with a failing test: `*.spec.ts(x)` for the
  legacy `app/` (Vite/React) tree, `tests/test_*.py` (pytest) for `digest-bot/`.
- **No skipping the retrospective.** Write `docs/retrospectives/NNN-<slug>.md` after every feature.
- **No governance files inside `app/` or `digest-bot/`.** `CLAUDE.md`, `README.md`, `docs/**` live
  at the repo root.
- **No product code at the repo root.** Per ADR 002-005, the bot lives under `digest-bot/app/`;
  the legacy `app/src/` (Vite/React) tree is not actively developed.
- **No `eslint-plugin-react` until it supports ESLint 10.** Use `eslint-plugin-react-hooks` instead
  (covers the important rules). Current Vite templates ship ESLint 10; the plugin is incompatible.
- **TypeScript strict mode is non-negotiable** for any code under `app/`. Do not disable `strict`,
  `noImplicitAny`, `strictNullChecks`, or `noUncheckedIndexedAccess`.
