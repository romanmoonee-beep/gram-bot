"""Состояния для настройки проверки подписок"""

from aiogram.fsm.state import State, StatesGroup

class SubscriptionSetupStates(StatesGroup):
    """Состояния для настройки ОП"""
    
    # Выбор типа
    choosing_type = State()
    
    # Публичные каналы
    entering_channel = State()
    setting_duration = State()
    
    # Приватные каналы
    entering_invite_link = State()
    
    # Реферальная ОП
    confirming_referral_setup = State()
    
    # Автоудаление
    setting_auto_delete = State()