"""Фильтры для callback данных"""

from typing import Any
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery

class CallbackDataFilter(BaseFilter):
    """Фильтр для проверки callback данных"""
    
    def __init__(self, prefix: str):
        self.prefix = prefix
    
    async def __call__(self, callback: CallbackQuery) -> bool:
        """Проверка префикса callback данных"""
        if not callback.data:
            return False
        return callback.data.startswith(self.prefix)