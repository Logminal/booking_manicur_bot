import logging
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states import BookingState
from database import get_services, add_booking, get_busy_times, get_user_bookings, delete_booking, get_service, get_work_hours
from keyboards import main_menu_kb
from config import ADMIN_ID

router = Router()


@router.callback_query(F.data == "book")
async def choose_service(callback: CallbackQuery, state: FSMContext):
    """Выбор услуги: показываем название, цену и примерную длительность"""
    await state.clear()
    services = await get_services()
    
    logging.info(f"Загруженные услуги: {services}")
    
    if not services:
        await callback.answer("Услуг пока нет. Добавьте их через админку.", show_alert=True)
        return
    
    kb = InlineKeyboardBuilder()
    for name, price, duration in services:
        dur = duration if duration else 0
        kb.button(text=f"{name} — от {price}₽ — {dur} мин", callback_data=f"svc_{name}")
    kb.adjust(1)
    kb.button(text="⬅️ Назад", callback_data="to_main")
    
    await callback.message.edit_text("Выберите услугу:", reply_markup=kb.as_markup())
    await state.set_state(BookingState.choosing_service)


@router.callback_query(F.data.startswith("svc_"))
async def choose_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты"""
    service = callback.data.replace("svc_", "")
    # достаём цену и длительность чтобы сохранять в состоянии
    info = await get_service(service)
    if info:
        price, duration = info
        duration = duration or 0
    else:
        price, duration = "", 0
    await state.update_data(service=service, price=price, duration=duration)
    
    kb = InlineKeyboardBuilder()
    today = datetime.now()
    for i in range(1, 8):
        day = today + timedelta(days=i)
        kb.button(text=day.strftime("%d.%m"), callback_data=f"date_{day.strftime('%Y-%m-%d')}")
    kb.adjust(3)
    kb.button(text="⬅️ Назад", callback_data="book")
    
    await callback.message.edit_text(
        f"Услуга: {service} — от {price}₽ — {duration} мин\nВыберите дату:",
        reply_markup=kb.as_markup()
    )
    await state.set_state(BookingState.choosing_date)


@router.callback_query(F.data.startswith("date_"))
async def choose_time(callback: CallbackQuery, state: FSMContext):
    """Выбор времени с учётом длительности и рабочих часов"""
    date = callback.data.replace("date_", "")
    await state.update_data(date=date)
    
    data = await state.get_data()
    duration = data.get('duration', 0)

    # часы работы
    start_str, end_str = await get_work_hours()
    day_start = datetime.fromisoformat(f"{date}T{start_str}")
    day_end = datetime.fromisoformat(f"{date}T{end_str}")

    # загружаем занятые интервалы
    busy = await get_busy_times(date)  # list of (time, dur)
    busy_intervals = []
    for t, d in busy:
        st = datetime.fromisoformat(f"{date}T{t}")
        busy_intervals.append((st, st + timedelta(minutes=d)))

    slots = []
    step = timedelta(minutes=30)  # шаг можно изменять
    current = day_start
    dur_delta = timedelta(minutes=duration)
    while current + dur_delta <= day_end:
        overlap = False
        for st, ed in busy_intervals:
            if not (current + dur_delta <= st or current >= ed):
                overlap = True
                break
        if not overlap:
            slots.append(current.strftime("%H:%M"))
        current += step

    kb = InlineKeyboardBuilder()
    for t in slots:
        kb.button(text=t, callback_data=f"time_{t}")
    kb.adjust(2)

    kb.button(text="⬅️ Назад", callback_data=f"svc_{data['service']}")

    await callback.message.edit_text(
        f"Дата: {date}\nСвободное время:",
        reply_markup=kb.as_markup()
    )
    await state.set_state(BookingState.choosing_time)


@router.callback_query(F.data.startswith("time_"))
async def confirm(callback: CallbackQuery, state: FSMContext):
    """Подтверждение записи"""
    time = callback.data.replace("time_", "")
    data = await state.update_data(time=time)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="finish")
    kb.button(text="❌ Отмена", callback_data="to_main")
    kb.adjust(1)
    
    await callback.message.edit_text(
        f"Подтвердите запись:\n💅 {data['service']} - от {data.get('price','')}₽ - {data.get('duration',0)}мин\n📅 {data['date']}\n⏰ {data['time']}",
        reply_markup=kb.as_markup()
    )
    await state.set_state(BookingState.confirming)


@router.callback_query(F.data == "finish")
async def finish(callback: CallbackQuery, state: FSMContext):
    """Завершение записи"""
    from bot import bot
    
    data = await state.get_data()
    
    await add_booking(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        service=data['service'],
        date=data['date'],
        time=data['time'],
        duration=data.get('duration',0)
    )
    
    await callback.message.edit_text(
        "🎉 Вы успешно записаны!",
        reply_markup=main_menu_kb(callback.from_user.id)
    )
    
    # Уведомление мастеру
    note_text = f"🔔 Новая запись: @{callback.from_user.username}\n{data['service']} - {data['date']} {data['time']}"
    logging.info(f"admin notification: {note_text}")
    if ADMIN_ID:
        for admin_id in ADMIN_ID:
            try:
                await bot.send_message(admin_id, note_text)
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")
    else:
        logging.warning("ADMIN_ID не задан, уведомление не отправлено")
    
    await state.clear()


@router.callback_query(F.data == "my_bookings")
async def my_bookings(callback: CallbackQuery):
    """Просмотр записей пользователя"""
    bookings = await get_user_bookings(callback.from_user.id, datetime.now().strftime("%Y-%m-%d"))
    
    if not bookings:
        await callback.answer("У вас нет активных записей.", show_alert=True)
        return
    
    text = "📅 Ваши записи:\n\n"
    kb = InlineKeyboardBuilder()
    for booking_id, service, date, time, duration, status in bookings:
        text += f"📍 {date} {time} — {service} ({duration} мин) | статус: {status}\n"
        kb.button(text=f"❌ Отменить {date}", callback_data=f"del_{booking_id}")
    
    kb.button(text="⬅️ В меню", callback_data="to_main")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("del_"))
async def del_booking(callback: CallbackQuery):
    """Отмена записи"""
    booking_id = int(callback.data.replace("del_", ""))
    await delete_booking(booking_id)
    await callback.answer("Запись отменена!")
    await my_bookings(callback)
