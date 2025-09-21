from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from app.services.user_service import UserService
from app.services.transaction_service import TransactionService
from app.services.task_service import TaskService

class DatabaseMiddleware(BaseMiddleware):
    """Middleware для внедрения сервисов в обработчики"""
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Внедряем сервисы в данные обработчика
        data["user_service"] = UserService()
        data["transaction_service"] = TransactionService()
        data["task_service"] = TaskService()
        
        return await handler(event, data)
