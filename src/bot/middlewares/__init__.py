from aiogram import Dispatcher

from app.bot.middlewares.database import DatabaseMiddleware
from app.bot.middlewares.auth import AuthMiddleware
from app.bot.middlewares.rate_limit import RateLimitMiddleware
from app.bot.middlewares.logging import LoggingMiddleware

def register_all_middlewares(dp: Dispatcher) -> None:
    """Регистрация всех middlewares в правильном порядке"""
    
    # 1. Логирование (первый - видит все запросы)
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    
    # 2. Ограничение частоты запросов
    dp.message.middleware(RateLimitMiddleware())
    dp.callback_query.middleware(RateLimitMiddleware())
    
    # 3. Внедрение сервисов
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    
    # 4. Аутентификация пользователей (последний)
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())