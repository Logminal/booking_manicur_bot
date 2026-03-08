from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_ID


def main_menu_kb(user_id: int):
    """Главное меню"""
    kb = InlineKeyboardBuilder()
    kb.button(text="💅 Записаться", callback_data="book")
    kb.button(text="📅 Мои записи", callback_data="my_bookings")
    
    if user_id in ADMIN_ID:
        kb.button(text="🛠 Админка", callback_data="admin_panel")
    
    kb.adjust(1)
    return kb.as_markup()


def admin_panel_kb():
    """Админ панель"""
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить услугу", callback_data="add_svc")
    kb.button(text="📋 Список всех записей", callback_data="view_all_bookings")
    kb.button(text="⏰ Часы работы", callback_data="set_hours")
    kb.button(text="⬅️ Назад", callback_data="to_main")
    kb.adjust(1)
    return kb.as_markup()


def back_to_admin_kb():
    """Кнопка назад в админ панель"""
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="admin_panel")
    return kb.as_markup()
