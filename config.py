import os
import logging
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загрузка переменных окружения
load_dotenv()

# ВАЖНО: приводим к списку int сразу при загрузке
BOT_TOKEN = os.getenv("BOT_TOKEN")
try:
    admin_ids = os.getenv("ADMIN_ID", "").strip()
    ADMIN_ID = [int(x.strip()) for x in admin_ids.split(",") if x.strip()]
    if not ADMIN_ID:
        ADMIN_ID = []
        logging.error("ОШИБКА: ADMIN_ID не найден или пустой в .env!")
except (TypeError, ValueError) as e:
    ADMIN_ID = []
    logging.error(f"ОШИБКА: ADMIN_ID имеет неверный формат в .env! {e}")

DB_NAME = "nails.db"
