# ADR 001 — Repository layout: root governance + app/ subfolder

## Status
Accepted

## Context

We need a consistent layout that separates agentic governance files (CLAUDE.md, docs/) from
application code (Vite + React + TS). Mixing them causes confusion: Claude reads governance
files on every turn, so they must be easy to locate; Vite tooling expects its config at a
predictable root.

## Decision

- All Vite/React/TS code lives under `app/`.
- All governance files (`CLAUDE.md`, `README.md`, `docs/**`) live at the repo root.
- Root `package.json` contains pass-through scripts (`npm --prefix app run <cmd>`).
- A single root-level `.gitignore` replaces Vite's default `app/.gitignore`.
- `docs/` is subdivided into `requirements/`, `decisions/`, `retrospectives/`, and `constraints.md`.

## Consequences

- `npm run dev` (and all commands) work from the repo root — no need to `cd app`.
- Claude's context window always starts with governance at the root; app code is isolated.
- Adding a second package (e.g. `packages/shared/`) in the future may warrant switching the
  root `package.json` to npm workspaces (record in a new ADR at that time).
- `eslint-plugin-react` is incompatible with ESLint 10 (shipped by current Vite templates);
  `eslint-plugin-react-hooks` covers the important rules. See `docs/constraints.md`.
