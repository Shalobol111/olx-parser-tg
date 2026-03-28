from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import main_menu_router, parsing_router, settings_router
from handlers.parsing import scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set. Create a .env file with BOT_TOKEN=<your_token>.")
        sys.exit(1)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(main_menu_router)
    dp.include_router(parsing_router)
    dp.include_router(settings_router)

    logger.info("Bot is starting…")
    try:
        await dp.start_polling(bot)
    finally:
        await scraper.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
