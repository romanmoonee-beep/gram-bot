"""Фильтры для проверки прав администратора"""

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from app.config.settings import settings

class AdminFilter(BaseFilter):
    """Фильтр для проверки администратора"""
    
    async def __call__(self, update: Message | CallbackQuery) -> bool:
        """Проверка является ли пользователь админом"""
        user_id = update.from_user.id
        return user_id in settings.ADMIN_IDS

class IsSuperAdminFilter(BaseFilter):
    """Фильтр для проверки супер-администратора"""
    
    def __init__(self, super_admin_id: int):
        self.super_admin_id = super_admin_id
    
    async def __call__(self, update: Message | CallbackQuery) -> bool:
        """Проверка является ли пользователь супер-админом"""
        return update.from_user.id == self.super_admin_id