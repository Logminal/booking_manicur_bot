# main.py больше не создаёт экземпляры бота/диспетчера,
# они вынесены в bot.py, чтобы избежать циклических импортов.
import asyncio
import logging

from database import init_db
from handlers import common, booking, admin
from bot import bot, dp, scheduler

# Подключение обработчиков: специфичные роутеры первыми, общий последний
dp.include_router(booking.router)
dp.include_router(admin.router)
dp.include_router(common.router)
# Подключение обработчиков


async def main():
    """Главная функция"""
    logging.info("Инициализация БД...")
    await init_db()
    
    logging.info("Запуск планировщика...")
    scheduler.start()
    
    logging.info("Запуск polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())