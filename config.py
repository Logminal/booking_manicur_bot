import os
import logging
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загрузка переменных окружения
load_dotenv()

# ВАЖНО: приводим к int сразу при загрузке
BOT_TOKEN = os.getenv("BOT_TOKEN")
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID"))
except (TypeError, ValueError):
    ADMIN_ID = 0
    logging.error("ОШИБКА: ADMIN_ID не найден в .env или имеет неверный формат!")

DB_NAME = "nails.db"
