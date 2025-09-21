"""Состояния для создания заданий"""

from aiogram.fsm.state import State, StatesGroup

class TaskCreationStates(StatesGroup):
    """Состояния для создания задания"""
    
    # Выбор типа
    choosing_type = State()
    
    # Основные параметры
    entering_title = State()
    entering_description = State()
    entering_url = State()
    entering_reward = State()
    entering_quantity = State()
    
    # Дополнительные настройки
    setting_duration = State()
    setting_requirements = State()
    setting_auto_check = State()
    
    # Подтверждение
    confirmation = State()