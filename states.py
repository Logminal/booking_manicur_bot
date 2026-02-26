from aiogram.fsm.state import StatesGroup, State


class BookingState(StatesGroup):
    """Состояния для процесса бронирования"""
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()
    confirming = State()


class AdminState(StatesGroup):
    """Состояния для админ панели"""
    adding_service_name = State()
    adding_service_price = State()
    adding_service_duration = State()
    setting_hours = State()  # ввод часов работы