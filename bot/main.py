from telegram.ext import Application
import logging
from telegram.error import Conflict

from config import config
from bot import handlers


def main() -> None:
    """Start the Telegram bot using configuration from ``config``."""
    app = Application.builder().token(config.telegram_token).build()
    handlers.setup(app)
    try:
        app.run_polling(drop_pending_updates=True)
    except Conflict:
        logging.error("Another instance of the bot is already running.")
        raise


if __name__ == "__main__":
    main()
