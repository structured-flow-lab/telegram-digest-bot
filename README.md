# telegram-digest-bot

A Telegram bot that reads selected public Telegram channels and replies with a
short AI-generated digest for a requested time period — a per-channel
table of contents with links back to the original posts.

## Quick start (digest-bot)

```bash
cd digest-bot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r dev-requirements.txt
copy .env.example .env   # fill in tokens/keys, see docs/deployment.md
python scripts/telethon_login.py   # one-time interactive Telethon login
python app/main.py
```

Then talk to your bot on Telegram: `/start`, `/add @channel`, `/digest 7`.

See [docs/deployment.md](docs/deployment.md) for full local setup and
deploying to Railway.

## Layout

- `CLAUDE.md` — how Claude works in this repo
- `docs/` — requirements, decisions (ADRs), retrospectives, constraints,
  deployment guide
- `digest-bot/` — the bot (Python, `python-telegram-bot` + Telethon + SQLite
  + Claude) — this is the product
- `app/` — original Vite/React bootstrap from feature 001; not actively
  developed (see ADR 002-005)

## Commands (digest-bot, from `digest-bot/`)

| Command | What it does |
|---|---|
| `python app/main.py` | Run the bot (polling) |
| `python -m pytest` | Run tests |
| `python scripts/telethon_login.py` | One-time interactive Telethon login |

## Working agreement

Spec-first, ADR-required for new patterns, retro after every feature. See [CLAUDE.md](./CLAUDE.md).
