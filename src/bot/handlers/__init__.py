from aiogram import Dispatcher

from app.bot.handlers import (
    start,
    menu,
    profile,
    earn,
    advertise,
    referral,
    payments,
    settings,  # Добавляем настройки
    admin,     # Добавляем админку
    checks,    # Добавляем чеки
    common,
)

def register_all_handlers(dp: Dispatcher) -> None:
    """Регистрация всех обработчиков в правильном порядке"""
    
    # Порядок важен! Более специфичные handlers должны быть выше
    
    # 1. Стартовые команды (высший приоритет)
    dp.include_router(start.router)
    
    # 2. Админские команды (высокий приоритет, после старта)
    dp.include_router(admin.router)
    
    # 3. Основные модули (средний приоритет)
    dp.include_router(profile.router)
    dp.include_router(earn.router) 
    dp.include_router(advertise.router)
    dp.include_router(referral.router)
    dp.include_router(payments.router)
    dp.include_router(checks.router)
    dp.include_router(settings.router)  # Добавляем настройки
    
    # 4. Главное меню (средний приоритет)
    dp.include_router(menu.router)
    
    # 5. Общие команды (низший приоритет)
    dp.include_router(common.router)
