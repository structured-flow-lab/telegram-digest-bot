"""Entry point — initialise and run the bot."""

import logging
import os
import sys

from telegram.ext import Application, CommandHandler

# Ensure "app" package is importable when running as "python app/main.py" from
# the digest-bot/ directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config
from app.bot.handlers import (
    add_handler,
    channels_handler,
    digest_handler,
    help_handler,
    remove_handler,
    start_handler,
)
from app.storage.db import get_connection
from app.storage.migrations import run_migrations

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def _init_db(application: Application) -> None:
    """Run migrations before the bot starts accepting updates."""
    async with get_connection() as conn:
        await run_migrations(conn)
    logger.info("Database ready")


def main() -> None:
    application = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(_init_db)
        .build()
    )

    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("add", add_handler))
    application.add_handler(CommandHandler("remove", remove_handler))
    application.add_handler(CommandHandler("channels", channels_handler))
    application.add_handler(CommandHandler("digest", digest_handler))

    logger.info("Starting bot in polling mode (owner_id=%d)", config.OWNER_TELEGRAM_ID)
    # Drop updates queued while the bot was offline rather than replaying them on restart.
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
