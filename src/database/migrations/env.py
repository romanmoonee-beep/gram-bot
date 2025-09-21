import asyncio
from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Добавляем корень проекта в Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.config.settings import settings
from app.database.database import Base

# Импортируем все модели для автогенерации
from app.database.models.user import User
from app.database.models.transaction import Transaction

# Конфигурация Alembic
config = context.config

# Интерпретируем config файл для логирования
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Метаданные для автогенерации миграций
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """
    Запуск миграций в 'offline' режиме.
    """
    # Убираем asyncpg для offline режима
    url = settings.DATABASE_URL.replace("+asyncpg", "")
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,  # Для SQLite совместимости
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """
    Запуск миграций в 'online' режиме с async поддержкой.
    """
    connectable = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
        echo=settings.DEBUG,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def do_run_migrations(connection):
    """Выполнение миграций в синхронном контексте"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()

# Определяем режим запуска
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
