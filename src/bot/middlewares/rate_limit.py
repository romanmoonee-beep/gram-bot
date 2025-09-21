import time
from typing import Callable, Dict, Any, Awaitable

import structlog
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from app.config.settings import settings

logger = structlog.get_logger(__name__)

class RateLimitMiddleware(BaseMiddleware):
    """Middleware для ограничения частоты запросов"""
    
    def __init__(self):
        # Хранилище последних действий пользователей
        self.user_actions: Dict[int, list[float]] = {}
        self.max_actions = settings.MAX_ACTIONS_PER_MINUTE
        self.window_seconds = 60
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        current_time = time.time()
        
        # Получаем список действий пользователя
        if user_id not in self.user_actions:
            self.user_actions[user_id] = []
        
        user_action_times = self.user_actions[user_id]
        
        # Удаляем старые действия (старше минуты)
        user_action_times[:] = [
            action_time for action_time in user_action_times
            if current_time - action_time < self.window_seconds
        ]
        
        # Проверяем лимит
        if len(user_action_times) >= self.max_actions:
            logger.warning(
                "⚠️ Rate limit exceeded",
                user_id=user_id,
                actions_count=len(user_action_times),
                max_actions=self.max_actions
            )
            
            if isinstance(event, Message):
                await event.answer(
                    "⏰ Слишком много запросов! Подождите немного перед следующим действием."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("⏰ Слишком быстро! Подождите немного", show_alert=True)
            
            return
        
        # Добавляем текущее действие
        user_action_times.append(current_time)
        
        return await handler(event, data)
