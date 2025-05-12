import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from handlers import register_handlers
from notifications import schedule_jobs
from dotenv import load_dotenv
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

TOKEN = os.getenv('BOT_TOKEN')


async def main():
    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    register_handlers(dp, bot)
    await schedule_jobs(bot)  # Если нужно планировать задачи

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())