import aiosqlite
import logging
from config import DB_NAME


async def init_db():
    """Инициализация базы данных, создаёт таблицы и добавляет новые колонки при необходимости"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS services(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price TEXT,
            duration INTEGER    -- примерное время выполнения в минутах
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS bookings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            service TEXT,
            date TEXT,
            time TEXT,
            duration INTEGER,
            status TEXT DEFAULT 'active'  -- active, done, canceled
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS reviews(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT
        )""")
        # Исправления структуры для старых баз
        try:
            await db.execute("ALTER TABLE services ADD COLUMN price TEXT")
        except:
            pass
        try:
            await db.execute("ALTER TABLE services ADD COLUMN duration INTEGER")
        except:
            pass
        try:
            await db.execute("ALTER TABLE bookings ADD COLUMN duration INTEGER")
        except:
            pass
        try:
            await db.execute("ALTER TABLE bookings ADD COLUMN status TEXT DEFAULT 'active'")
        except:
            pass
        await db.commit()


async def get_services():
    """Получить все услуги (name, price, duration)"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT name, price, duration FROM services") as cursor:
            return await cursor.fetchall()


async def add_service(name: str, price: str, duration: int):
    """Добавить услугу вместе с примерным временем выполнения (в минутах)"""
    logging.info(f"Добавляем услугу: {name} - {price}, duration={duration}min")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO services (name, price, duration) VALUES (?,?,?)", (name, price, duration))
        await db.commit()
    logging.info(f"✅ Услуга '{name}' успешно добавлена в БД")


async def add_booking(user_id: int, username: str, service: str, date: str, time: str, duration: int):
    """Добавить запись с продолжительностью"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO bookings (user_id, username, service, date, time, duration) VALUES (?,?,?,?,?,?)",
            (user_id, username, service, date, time, duration)
        )
        await db.commit()


async def get_user_bookings(user_id: int, current_date: str):
    """Получить записи пользователя, включая длительность и статус"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT id, service, date, time, duration, status FROM bookings WHERE user_id=? AND date >= ? ORDER BY date ASC",
            (user_id, current_date)
        ) as cursor:
            return await cursor.fetchall()


async def get_all_bookings():
    """Получить все записи с информацией о длительности и статусе"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, username, service, date, time, duration, status FROM bookings ORDER BY date ASC") as cursor:
            return await cursor.fetchall()


async def get_busy_times(date: str):
    """Получить занятые времена и длительности для даты"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT time, duration FROM bookings WHERE date=?", (date,)) as cursor:
            return await cursor.fetchall()  # list of tuples (time, duration)


async def get_service(name: str):
    """Получить информацию об услуге по названию (price, duration)"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT price, duration FROM services WHERE name=?", (name,)) as cursor:
            return await cursor.fetchone()  # (price, duration) or None


async def delete_booking(booking_id: int):
    """Удалить запись"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM bookings WHERE id=?", (booking_id,))
        await db.commit()


async def update_booking_status(booking_id: int, status: str):
    """Обновить статус записи (active, done, canceled)"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE bookings SET status=? WHERE id=?", (status, booking_id))
        await db.commit()


async def get_work_hours():
    """Возвращает кортеж строк (start,end) часов работы. По умолчанию 10:00-21:00"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT value FROM settings WHERE key='work_hours'") as cursor:
            row = await cursor.fetchone()
    if row and '-' in row[0]:
        return tuple(row[0].split('-'))
    return ("10:00", "21:00")


async def set_work_hours(start: str, end: str):
    """Сохранить часы работы в формате HH:MM-HH:MM"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key,value) VALUES ('work_hours',?)", (f"{start}-{end}",))
        await db.commit()
