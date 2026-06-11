"""Entry point — initialise and run the bot."""

import asyncio
import logging
import os
import sys

from telegram.ext import Application, CommandHandler

# Ensure "app" package is importable when running as "python app/main.py" from
# the digest-bot/ directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config
from app.bot.handlers import help_handler, start_handler
from app.storage.db import get_connection
from app.storage.migrations import run_migrations

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def _init_db() -> None:
    """Run migrations before the bot starts accepting updates."""
    async with get_connection() as conn:
        await run_migrations(conn)


def main() -> None:
    # Run DB migrations synchronously before the event loop starts.
    asyncio.run(_init_db())
    logger.info("Database ready")

    application = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .build()
    )

    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))

    logger.info("Starting bot in polling mode (owner_id=%d)", config.OWNER_TELEGRAM_ID)
    # Drop updates queued while the bot was offline rather than replaying them on restart.
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
