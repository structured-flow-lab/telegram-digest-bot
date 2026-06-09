# Retrospective 001 — Hello World Bootstrap

## What we did
Scaffolded `app/` with Vite + React + TypeScript, set up root pass-through scripts and dotfiles,
created the agentic governance skeleton (CLAUDE.md, README.md, docs/), then ran the full
spec-first hello-world loop: requirements doc → failing spec → `greeting.ts` module → green tests →
App.tsx wired up → dev server confirmed live at http://127.0.0.1:5173/ (curl 200, PID alive).

## What worked
- Root pass-through scripts (`npm run dev` from repo root) worked cleanly.
- Spec-first loop (red → green) demonstrated end-to-end in one cycle.
- Port probing via `nc` shim (PowerShell TCP wrapper) was transparent.
- Dev server came up on the default port 5173 — no conflict.

## What didn't / friction points
- `nc` (netcat) was not available on Windows; required installing nmap via winget and creating
  a PowerShell-backed bash shim at `~/bin/nc`. On a fresh Windows machine this is a manual step.
- `eslint-plugin-react` is incompatible with ESLint 10 shipped by current Vite templates —
  dropped in favour of `eslint-plugin-react-hooks` (recorded in constraints.md and ADR 001).
- `.claude/launch.json` must be created manually by the user in their own terminal (Claude Code
  self-modification classifier blocks writes to `.claude/` paths during bootstrap).
- Git user identity was not configured globally — required a per-repo `git config user.*` before
  the first commit could land.

## Decisions to carry forward
- See [docs/decisions/001-agent-structure.md](../decisions/001-agent-structure.md)

## Changes made to CLAUDE.md / constraints / working agreement
- None — workflow held up. Constraints.md already documents the eslint-plugin-react restriction.

## Open questions for next session
- None.
