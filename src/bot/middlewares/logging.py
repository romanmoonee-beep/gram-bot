from typing import Callable, Dict, Any, Awaitable

import structlog
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

logger = structlog.get_logger(__name__)

class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования действий пользователей"""
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user = event.from_user
        
        if isinstance(event, Message):
            logger.info(
                "📨 Message received",
                user_id=user.id,
                username=user.username,
                text=event.text[:100] if event.text else None,
                chat_type=event.chat.type
            )
        elif isinstance(event, CallbackQuery):
            logger.info(
                "🔘 Callback received",
                user_id=user.id,
                username=user.username,
                callback_data=event.data
            )
        
        try:
            result = await handler(event, data)
            return result
        except Exception as e:
            logger.error(
                "💥 Error in handler",
                user_id=user.id,
                username=user.username,
                error=str(e),
                exc_info=True
            )
            
            # Отправляем пользователю сообщение об ошибке
            error_message = "😔 Произошла ошибка. Попробуйте еще раз или обратитесь в поддержку."
            
            if isinstance(event, Message):
                await event.answer(error_message)
            elif isinstance(event, CallbackQuery):
                await event.answer(error_message, show_alert=True)
            
            raise