"""Фабрики для создания бота и диспетчера"""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from app.config.settings import settings

async def create_bot() -> Bot:
    """Создание экземпляра бота с настройками"""
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=True,
            protect_content=False
        )
    )

async def create_dispatcher() -> Dispatcher:
    """Создание диспетчера с Redis хранилищем"""
    # Redis для FSM состояний
    storage = RedisStorage.from_url(settings.REDIS_URL)
    
    # Создаем диспетчер
    dp = Dispatcher(storage=storage)
    
    # Регистрируем middlewares и handlers
    from app.bot.middlewares import register_all_middlewares
    from app.bot.handlers import register_all_handlers
    
    register_all_middlewares(dp)
    register_all_handlers(dp)
    
    return dp