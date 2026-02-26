import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states import AdminState
from config import ADMIN_ID
from database import add_service, get_all_bookings, update_booking_status, set_work_hours, get_work_hours
from keyboards import main_menu_kb, admin_panel_kb, back_to_admin_kb
from bot import dp, bot
from aiogram.fsm.storage.base import StorageKey

router = Router()


@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    """Админ панель"""
    if int(callback.from_user.id) != ADMIN_ID:
        await callback.answer(f"Доступ запрещен! Ваш ID: {callback.from_user.id}", show_alert=True)
        return
    
    kb = admin_panel_kb()
    await callback.message.edit_text("Панель управления мастером 🛠", reply_markup=kb)


@router.callback_query(F.data == "view_all_bookings")
async def view_all_bookings(callback: CallbackQuery):
    """Просмотр всех записей с возможностью пометить статус"""
    if int(callback.from_user.id) != ADMIN_ID:
        return
    
    bookings = await get_all_bookings()
    
    if not bookings:
        await callback.answer("Записей в базе пока нет.", show_alert=True)
        return
    
    text = "📋 Все записи клиентов:\n\n"
    kb = InlineKeyboardBuilder()
    for bid, username, service, date, time, duration, status in bookings:
        text += f"#{bid} @{username} | 📅 {date} {time} | 💅 {service} | ⏱ {duration} мин | статус: {status}\n"
        label = f"@{username} — {service}"
        kb.button(text=f"✅ {label}", callback_data=f"done_{bid}")
        kb.button(text=f"❌ {label}", callback_data=f"cancel_{bid}")
        kb.adjust(2)
    kb.button(text="⬅️ Назад", callback_data="admin_panel")
    kb.adjust(1)
    await callback.message.edit_text(text[:4000], reply_markup=kb.as_markup())


@router.callback_query(F.data == "add_svc")
async def add_svc_name(callback: CallbackQuery, state: FSMContext):
    """Начало добавления услуги. Устанавливаем state и для приватного чата"""
    if int(callback.from_user.id) != ADMIN_ID:
        return
    logging.info("admin: start adding service")
    await callback.message.edit_text("Название услуги (например: Маникюр + гель-лак):")
    # set state in current chat
    await state.set_state(AdminState.adding_service_name)
    # also set in private chat so admin can ответить туда
    key = StorageKey(bot_id=bot.id, chat_id=callback.from_user.id, user_id=callback.from_user.id)
    try:
        await dp.storage.set_state(key=key, state=AdminState.adding_service_name)
        logging.info(f"admin: set private storage state for key={key}")
    except Exception:
        logging.exception("admin: failed to set private storage state")


@router.callback_query(F.data == "set_hours")
async def set_hours_start(callback: CallbackQuery, state: FSMContext):
    """Запрос часов работы. дублируем состояние в приватный чат"""
    if int(callback.from_user.id) != ADMIN_ID:
        return
    
    hrs = await get_work_hours()
    await callback.message.edit_text(f"Текущие часы работы: {hrs[0]}-{hrs[1]}.\nВведите новые в формате HH:MM-HH:MM:")
    await state.set_state(AdminState.setting_hours)
    key = StorageKey(bot_id=bot.id, chat_id=callback.from_user.id, user_id=callback.from_user.id)
    try:
        await dp.storage.set_state(key=key, state=AdminState.setting_hours)
        logging.info(f"admin: set private storage state for setting_hours key={key}")
    except Exception:
        logging.exception("admin: failed to set private storage state for setting_hours")


@router.message(AdminState.adding_service_name)
async def add_svc_price(message: Message, state: FSMContext):
    """Ввод цены услуги"""
    logging.info(f"admin: received service name '{message.text}' chat_id={message.chat.id}")
    await state.update_data(name=message.text)
    # also update private context if different
    key = StorageKey(bot_id=bot.id, chat_id=message.from_user.id, user_id=message.from_user.id)
    try:
        await dp.storage.update_data(key=key, data={"name": message.text})
        await dp.storage.set_state(key=key, state=AdminState.adding_service_price)
        cur = await dp.storage.get_state(key=key)
        logging.info(f"admin: private storage updated, state={cur} for key={key}")
    except Exception:
        logging.exception("admin: failed to update private storage with name")
    await message.answer("✏️ Введите цену (только цифры):")
    await state.set_state(AdminState.adding_service_price)


@router.message(AdminState.adding_service_price)
async def ask_duration(message: Message, state: FSMContext):
    """После цены спрашиваем длительность"""
    logging.info(f"admin: received price '{message.text}' chat_id={message.chat.id}")
    await state.update_data(price=message.text)
    key = StorageKey(bot_id=bot.id, chat_id=message.from_user.id, user_id=message.from_user.id)
    try:
        await dp.storage.update_data(key=key, data={"price": message.text})
        await dp.storage.set_state(key=key, state=AdminState.adding_service_duration)
        cur = await dp.storage.get_state(key=key)
        logging.info(f"admin: private storage price set, state={cur} for key={key}")
    except Exception:
        logging.exception("admin: failed to update private storage with price")
    await message.answer("✏️ Введите примерное время выполнения услуги в минутах (например: 60):")
    await state.set_state(AdminState.adding_service_duration)


@router.message(AdminState.adding_service_duration)
async def add_svc_final(message: Message, state: FSMContext):
    """Завершение добавления услуги"""
    data = await state.get_data()
    logging.info(f"admin: received duration '{message.text}' with previous data {data}")
    try:
        duration = int(message.text)
    except ValueError:
        await message.answer("Неверный формат, укажите число минут.")
        return
    
    await add_service(data['name'], data['price'], duration)
    
    await message.answer(
        f"✅ Услуга '{data['name']}' добавлена!",
        reply_markup=main_menu_kb(message.from_user.id)
    )
    await state.clear()


# ======== Остальные админские хендлеры ========

@router.callback_query(F.data.startswith("done_"))
async def mark_done(callback: CallbackQuery):
    if int(callback.from_user.id) != ADMIN_ID:
        return
    bid = int(callback.data.replace("done_", ""))
    await update_booking_status(bid, "done")
    await callback.answer("Отмечено как завершено")
    await view_all_bookings(callback)


@router.callback_query(F.data.startswith("cancel_"))
async def mark_canceled(callback: CallbackQuery):
    if int(callback.from_user.id) != ADMIN_ID:
        return
    bid = int(callback.data.replace("cancel_", ""))
    await update_booking_status(bid, "canceled")
    await callback.answer("Отменено")
    await view_all_bookings(callback)


@router.message(AdminState.setting_hours)
async def save_hours(message: Message, state: FSMContext):
    """Сохранить часы работы"""
    parts = message.text.split("-")
    if len(parts) != 2:
        await message.answer("Неверный формат, используйте HH:MM-HH:MM")
        return
    start, end = parts
    await set_work_hours(start.strip(), end.strip())
    await message.answer(f"Часы работы сохранены: {start}-{end}")
    # clear both contexts
    key = StorageKey(bot_id=bot.id, chat_id=message.from_user.id, user_id=message.from_user.id)
    await dp.storage.set_state(key=key, state=None)
    await dp.storage.set_data(key=key, data={})
    await state.clear()


