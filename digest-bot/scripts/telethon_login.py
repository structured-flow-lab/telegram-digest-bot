"""One-time interactive Telethon login. Run manually:

    cd digest-bot
    .venv\\Scripts\\python scripts\\telethon_login.py

Creates/authorises data/telethon.session using your phone number + login code
(and 2FA password if enabled). Run this from a real terminal, not via an
automated tool, since it needs interactive input.
"""

import os
import sys

from dotenv import load_dotenv
from telethon import TelegramClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

SESSION_PATH = "data/telethon.session"


def main() -> None:
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]

    client = TelegramClient(SESSION_PATH, api_id, api_hash)
    client.start()
    print("Logged in successfully. Session saved to", SESSION_PATH)
    client.disconnect()


if __name__ == "__main__":
    main()
