# telegram-digest-bot

A web application that reads selected public Telegram channels and generates a short AI digest for a requested time period.

## Quick start

```bash
npm run setup        # installs app/ deps
npm run dev          # starts http://127.0.0.1:5173/
```

## Layout

- `CLAUDE.md` — how Claude works in this repo
- `docs/` — requirements, decisions (ADRs), retrospectives, constraints
- `app/` — Vite + React + TypeScript application code

## Commands (all from repo root)

`npm run dev | build | preview | test | lint | format`

## Working agreement

Spec-first, ADR-required for new patterns, retro after every feature. See [CLAUDE.md](./CLAUDE.md).
