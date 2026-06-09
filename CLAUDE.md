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
  app/                        ← ALL Vite + React + TS code lives here
    src/
    vite.config.ts
    vitest.config.ts
    package.json
    ...
```

Governance files (`CLAUDE.md`, `README.md`, `docs/**`) live at the repo root — never inside `app/`.
App code lives inside `app/` — never at the repo root.

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
10. **Layout discipline.** Governance files live at repo root, never inside `app/`. App code lives inside `app/`, never at repo root.
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

- [docs/requirements/overview.md](docs/requirements/overview.md)
- [docs/decisions/001-agent-structure.md](docs/decisions/001-agent-structure.md)
- [docs/constraints.md](docs/constraints.md)
- [docs/retrospectives/](docs/retrospectives/) ← populated after each feature

---

## Current state

Hello world greeting rendered; no features specced.

---

## Self-improvement log

_(populated after each retrospective)_
