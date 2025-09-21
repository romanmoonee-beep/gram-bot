"""Состояния для админской панели"""

from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    """Состояния админской панели"""
    
    # Модерация
    reviewing_task = State()
    entering_reject_reason = State()
    
    # Управление пользователями
    entering_user_id = State()
    entering_ban_reason = State()
    entering_bonus_amount = State()
    
    # Системные функции
    confirming_action = State()
    entering_broadcast_message = State()
