"""Состояния для выполнения заданий"""

from aiogram.fsm.state import State, StatesGroup

class TaskExecutionStates(StatesGroup):
    """Состояния для выполнения заданий"""
    
    # Выполнение
    waiting_confirmation = State()
    uploading_screenshot = State()
    entering_comment = State()
    
    # Проверка
    waiting_review = State()
    manual_check = State()