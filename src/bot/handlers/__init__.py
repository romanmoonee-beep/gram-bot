from aiogram import Dispatcher

from app.bot.handlers import (
    start,
    menu,
    profile,
    earn,
    advertise,
    referral,
    payments,
    common,
)

def register_all_handlers(dp: Dispatcher) -> None:
    """Регистрация всех обработчиков в правильном порядке"""
    
    # Порядок важен! Более специфичные handlers должны быть выше
    
    # 1. Стартовые команды (высший приоритет)
    dp.include_router(start.router)
    
    # 2. Основные модули
    dp.include_router(profile.router)
    dp.include_router(earn.router) 
    dp.include_router(advertise.router)
    dp.include_router(referral.router)
    dp.include_router(payments.router)
    
    # 3. Главное меню (средний приоритет)
    dp.include_router(menu.router)
    
    # 4. Общие команды (низший приоритет)
    dp.include_router(common.router)

