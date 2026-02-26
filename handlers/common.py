import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from states import BookingState
from keyboards import main_menu_kb

router = Router()


@router.message(Command("start"))
async def start(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        f"Привет, {message.from_user.first_name}! 💖\nЯ бот для записи на маникюр.",
        reply_markup=main_menu_kb(message.from_user.id)
    )


@router.message(BookingState.choosing_service)
async def handle_booking_messages(message: Message):
    """Обработчик сообщений при выборе услуги"""
    await message.answer("Пожалуйста, выбирайте услугу через кнопки 👇")


@router.message(BookingState.choosing_date)
async def handle_booking_date_messages(message: Message):
    """Обработчик сообщений при выборе даты"""
    await message.answer("Пожалуйста, выбирайте дату через кнопки 👇")


@router.message(BookingState.choosing_time)
async def handle_booking_time_messages(message: Message):
    """Обработчик сообщений при выборе времени"""
    await message.answer("Пожалуйста, выбирайте время через кнопки 👇")


@router.message(BookingState.confirming)
async def handle_booking_confirm_messages(message: Message):
    """Обработчик сообщений при подтверждении"""
    await message.answer("Пожалуйста, подтвердите или отмените запись через кнопки 👇")


@router.message()
async def echo(message: Message, state: FSMContext):
    """Обработчик для всех остальных текстовых сообщений.
    Игнорирует сообщения при активном FSM-состоянии."""
    current = await state.get_state()
    logging.info(f"common: incoming message chat_id={message.chat.id} user_id={message.from_user.id} state={current}")
    if current:
        # есть активное состояние, ничего не делаем
        logging.info("common: skipping echo because FSM state is active")
        return

    await message.answer(
        "Пожалуйста, используйте кнопки меню ниже 👇",
        reply_markup=main_menu_kb(message.from_user.id)
    )


@router.callback_query(F.data == "to_main")
async def to_main(callback: CallbackQuery, state: FSMContext):
    """Вернуться в главное меню"""
    await state.clear()
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=main_menu_kb(callback.from_user.id)
    )
