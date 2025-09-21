from typing import Callable, Dict, Any, Awaitable

import structlog
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from app.services.user_service import UserService

logger = structlog.get_logger(__name__)

class AuthMiddleware(BaseMiddleware):
    """Middleware для аутентификации и создания пользователей"""
    
    def __init__(self):
        self.user_service = UserService()
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем пользователя из БД
        user = await self.user_service.get_user(event.from_user.id)
        
        if not user:
            # Если пользователь не найден, создаем его только для команды /start
            if isinstance(event, Message) and event.text and event.text.startswith('/start'):
                # Создание пользователя произойдет в обработчике /start
                pass
            else:
                # Для всех остальных команд отправляем в /start
                if isinstance(event, Message):
                    await event.answer(
                        "👋 Добро пожаловать! Нажмите /start для начала работы с ботом.",
                        reply_markup=None
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer("Нажмите /start для начала работы", show_alert=True)
                return
        else:
            # Проверяем, не заблокирован ли пользователь
            if user.is_banned:
                ban_message = f"❌ Ваш аккаунт заблокирован.\n\n📝 Причина: {user.ban_reason}"
                
                if isinstance(event, Message):
                    await event.answer(ban_message)
                elif isinstance(event, CallbackQuery):
                    await event.answer("❌ Ваш аккаунт заблокирован", show_alert=True)
                return
            
            # Обновляем время последней активности
            await self.user_service.update_last_activity(user.telegram_id)
            
            # Добавляем пользователя в данные для обработчиков
            data["user"] = user
        
        return await handler(event, data)