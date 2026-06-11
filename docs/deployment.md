# Deployment — digest-bot

The bot runs in **polling mode** everywhere (local and Railway) — see
[feature-006](requirements/feature-006-phase4-polish-deploy.md) and
[ADR 005](decisions/005-bot-framework-and-hosting.md). No public HTTPS
endpoint is needed.

## Local setup

1. `cd digest-bot`
2. Create a virtualenv and install deps:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt -r dev-requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in:
   - `TELEGRAM_BOT_TOKEN` — from @BotFather
   - `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` — from https://my.telegram.org
   - `ANTHROPIC_API_KEY` — from https://console.anthropic.com
   - `OWNER_TELEGRAM_ID` — your Telegram user ID (e.g. via @userinfobot)
4. One-time Telethon login (interactive, run from a real terminal):
   ```
   python scripts/telethon_login.py
   ```
   This creates `data/telethon.session`.
5. Run the bot:
   ```
   python app/main.py
   ```

## Deploying to Railway

Railway runs the container as a persistent process — polling works exactly
as it does locally.

1. **Create a Railway project** and connect this GitHub repo. Set the
   service's root directory to `digest-bot/` (so Railway finds the
   `Dockerfile` there).
2. **Set environment variables** on the Railway service — same names as
   `.env.example`:
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`,
     `ANTHROPIC_API_KEY`, `OWNER_TELEGRAM_ID`
   - `DB_PATH=data/digest_bot.sqlite`
   - `LLM_PROVIDER=claude`, `LLM_MODEL=claude-haiku-4-5-20251001`
3. **Add a persistent volume** mounted at `/app/data`. This is required for
   two things to survive restarts/redeploys:
   - the SQLite database file (`digest_bot.sqlite`)
   - the Telethon session file (`telethon.session`)
4. **Provide the Telethon session.** Interactive login (step 4 above) cannot
   run on Railway. Run `scripts/telethon_login.py` locally once, then upload
   the resulting `data/telethon.session` file into the Railway volume (e.g.
   via Railway's volume browser, or `railway run` / SSH into the service).
5. **Deploy.** Railway builds the `Dockerfile` and starts
   `python app/main.py`. Check the deploy logs for
   `"Starting bot in polling mode"` and `"Database ready"`.

## Inspecting errors

Unexpected errors are logged to the console **and** persisted to the
`errors` table in the SQLite DB (see feature-006). To inspect them, open
the DB file (locally or via the Railway volume) with any SQLite client:

```sql
SELECT * FROM errors ORDER BY occurred_at DESC LIMIT 20;
```
