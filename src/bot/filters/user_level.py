"""Фильтры для проверки уровня пользователя"""

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from app.database.models.user import UserLevel
from app.services.user_service import UserService

class UserLevelFilter(BaseFilter):
    """Фильтр для проверки уровня пользователя"""
    
    def __init__(self, level: UserLevel):
        self.level = level
        
    async def __call__(self, update: Message | CallbackQuery) -> bool:
        """Проверка уровня пользователя"""
        user_service = UserService()
        user = await user_service.get_user(update.from_user.id)
        
        if not user:
            return False
            
        return user.level == self.level

class MinLevelFilter(BaseFilter):
    """Фильтр для проверки минимального уровня пользователя"""
    
    def __init__(self, min_level: UserLevel):
        self.min_level = min_level
        self.level_hierarchy = [
            UserLevel.BRONZE,
            UserLevel.SILVER, 
            UserLevel.GOLD,
            UserLevel.PREMIUM
        ]
        
    async def __call__(self, update: Message | CallbackQuery) -> bool:
        """Проверка минимального уровня"""
        user_service = UserService()
        user = await user_service.get_user(update.from_user.id)
        
        if not user:
            return False
            
        try:
            user_index = self.level_hierarchy.index(user.level)
            min_index = self.level_hierarchy.index(self.min_level)
            return user_index >= min_index
        except ValueError:
            return False