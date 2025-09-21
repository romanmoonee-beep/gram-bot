"""Декораторы для обработчиков"""

import functools
import time
from typing import Callable, Any, Dict

import structlog
from aiogram.types import Message, CallbackQuery

logger = structlog.get_logger(__name__)

def rate_limit(rate: int = 1):
    """
    Декоратор для ограничения частоты вызовов
    
    Args:
        rate: Количество секунд между вызовами
    """
    def decorator(func: Callable) -> Callable:
        # Хранилище времени последних вызовов
        last_call_times: Dict[int, float] = {}
        
        @functools.wraps(func)
        async def wrapper(update: Message | CallbackQuery, *args, **kwargs):
            user_id = update.from_user.id
            current_time = time.time()
            
            # Проверяем время последнего вызова
            if user_id in last_call_times:
                time_passed = current_time - last_call_times[user_id]
                if time_passed < rate:
                    # Слишком быстро
                    if isinstance(update, CallbackQuery):
                        await update.answer("⏰ Слишком быстро!", show_alert=True)
                    else:
                        await update.answer("⏰ Подождите немного перед следующим действием")
                    return
            
            # Обновляем время последнего вызова
            last_call_times[user_id] = current_time
            
            # Вызываем оригинальную функцию
            return await func(update, *args, **kwargs)
        
        return wrapper
    return decorator

def admin_required(func: Callable) -> Callable:
    """Декоратор для проверки прав администратора"""
    
    @functools.wraps(func)
    async def wrapper(update: Message | CallbackQuery, *args, **kwargs):
        from app.config.settings import settings
        
        user_id = update.from_user.id
        
        if user_id not in settings.ADMIN_IDS:
            if isinstance(update, CallbackQuery):
                await update.answer("🚫 Доступ запрещен", show_alert=True)
            else:
                await update.answer("🚫 У вас нет прав для выполнения этого действия")
            return
        
        return await func(update, *args, **kwargs)
    
    return wrapper

def log_action(action_name: str):
    """Декоратор для логирования действий пользователей"""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(update: Message | CallbackQuery, *args, **kwargs):
            user_id = update.from_user.id
            username = update.from_user.username
            
            logger.info(
                "User action",
                action=action_name,
                user_id=user_id,
                username=username
            )
            
            try:
                result = await func(update, *args, **kwargs)
                
                logger.info(
                    "Action completed",
                    action=action_name,
                    user_id=user_id,
                    status="success"
                )
                
                return result
                
            except Exception as e:
                logger.error(
                    "Action failed",
                    action=action_name,
                    user_id=user_id,
                    error=str(e),
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator

def error_handler(func: Callable) -> Callable:
    """Декоратор для обработки ошибок"""
    
    @functools.wraps(func)
    async def wrapper(update: Message | CallbackQuery, *args, **kwargs):
        try:
            return await func(update, *args, **kwargs)
        except Exception as e:
            logger.error(
                "Handler error",
                handler=func.__name__,
                user_id=update.from_user.id,
                error=str(e),
                exc_info=True
            )
            
            error_message = "😔 Произошла ошибка. Попробуйте еще раз или обратитесь в поддержку."
            
            if isinstance(update, CallbackQuery):
                await update.answer(error_message, show_alert=True)
            else:
                await update.answer(error_message)
    
    return wrapper