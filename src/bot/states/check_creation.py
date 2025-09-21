"""Состояния для создания чеков"""

from aiogram.fsm.state import State, StatesGroup

class CheckCreationStates(StatesGroup):
    """Состояния для создания чеков"""
    
    # Тип чека
    choosing_type = State()
    
    # Персональный чек
    entering_amount = State()
    entering_recipient = State()
    entering_comment = State()
    entering_password = State()
    
    # Мульти чек
    entering_total_amount = State()
    entering_activations = State()
    setting_conditions = State()
    
    # Подтверждение
    confirmation = State()