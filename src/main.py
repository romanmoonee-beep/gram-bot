import asyncio
import logging
import sys

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from app.config.settings import settings
from app.database.database import init_db
from app.bot.handlers import register_all_handlers
from app.bot.middlewares import register_all_middlewares

# Настройка структурированного логирования
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.dev.ConsoleRenderer() if settings.DEBUG else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.INFO if not settings.DEBUG else logging.DEBUG
    ),
    logger_factory=structlog.WriteLoggerFactory(),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger(__name__)

async def create_bot() -> Bot:
    """Создание экземпляра бота"""
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
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)
    
    # Регистрируем middlewares и handlers
    register_all_middlewares(dp)
    register_all_handlers(dp)
    
    return dp

async def set_bot_commands(bot: Bot) -> None:
    """Установка команд бота"""
    commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="help", description="❓ Помощь"),
        BotCommand(command="menu", description="🏠 Главное меню"),
        BotCommand(command="profile", description="👤 Мой профиль"),
        BotCommand(command="earn", description="💰 Заработать"),
        BotCommand(command="advertise", description="📢 Рекламировать"),
        BotCommand(command="referral", description="🔗 Реферальная система"),
        BotCommand(command="balance", description="💰 Баланс"),
    ]
    
    await bot.set_my_commands(commands)

async def on_startup(bot: Bot) -> None:
    """Действия при запуске бота"""
    logger.info("🚀 Starting PR GRAM Bot...")
    
    # Инициализируем БД
    await init_db()
    logger.info("✅ Database initialized")
    
    # Устанавливаем команды бота
    await set_bot_commands(bot)
    logger.info("✅ Bot commands set")
    
    # Получаем информацию о боте
    bot_info = await bot.get_me()
    logger.info(
        "🤖 Bot started successfully",
        username=bot_info.username,
        first_name=bot_info.first_name,
        id=bot_info.id,
        environment=settings.ENVIRONMENT
    )

async def on_shutdown(bot: Bot) -> None:
    """Действия при остановке бота"""
    logger.info("🛑 Shutting down PR GRAM Bot...")
    
    # Удаляем webhook если был установлен
    await bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("✅ Bot stopped gracefully")

async def main() -> None:
    """Основная функция запуска"""
    try:
        # Создаем бот и диспетчер
        bot = await create_bot()
        dp = await create_dispatcher()
        
        # Регистрируем startup/shutdown handlers
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        if settings.WEBHOOK_URL and not settings.DEBUG:
            # Webhook режим (для продакшн)
            logger.info("🌐 Starting in webhook mode", webhook_url=settings.WEBHOOK_URL)
            
            # Настраиваем webhook
            webhook_requests_handler = SimpleRequestHandler(
                dispatcher=dp,
                bot=bot,
                secret_token=settings.WEBHOOK_SECRET
            )
            
            # Создаем aiohttp приложение
            app = web.Application()
            webhook_requests_handler.register(app, path="/webhook")
            setup_application(app, dp, bot=bot)
            
            # Устанавливаем webhook
            await bot.set_webhook(
                url=f"{settings.WEBHOOK_URL}/webhook",
                secret_token=settings.WEBHOOK_SECRET,
                drop_pending_updates=True
            )
            
            # Запускаем веб-сервер
            web.run_app(app, host="0.0.0.0", port=8000)
        else:
            # Polling режим (для разработки)
            logger.info("🔄 Starting in polling mode")
            
            await dp.start_polling(
                bot,
                allowed_updates=dp.resolve_used_update_types(),
                drop_pending_updates=True
            )
            
    except Exception as e:
        logger.error("💥 Fatal error during bot execution", error=str(e), exc_info=True)
        sys.exit(1)
    finally:
        if 'bot' in locals():
            await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error("💥 Unexpected error", error=str(e), exc_info=True)
        sys.exit(1)