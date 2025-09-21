from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from sqlalchemy import MetaData, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config.settings import settings

logger = structlog.get_logger(__name__)

# Современная конвенция именования для PostgreSQL
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

class Base(DeclarativeBase):
    """Базовый класс для всех моделей с современными аннотациями"""
    metadata = MetaData(naming_convention=convention)

# Создание движка с современными настройками
def create_engine() -> AsyncEngine:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        echo_pool=settings.DEBUG,
        # Современные настройки пула для высоконагруженных приложений
        pool_size=50,
        max_overflow=100,
        pool_pre_ping=True,
        pool_recycle=3600,
        # Для продакшена можно использовать NullPool с pgbouncer
        poolclass=NullPool if settings.USE_PGBOUNCER else None,
        # JSON сериализация для PostgreSQL
        json_serializer=lambda obj: settings.json_dumps(obj),
        json_deserializer=lambda obj: settings.json_loads(obj),
    )
    
    # Логирование медленных запросов в production
    if not settings.DEBUG:
        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()

        @event.listens_for(engine.sync_engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total = time.time() - context._query_start_time
            if total > 0.5:  # Логируем запросы дольше 500ms
                logger.warning("Slow query detected", duration=total, query=statement[:200])
    
    return engine

engine = create_engine()

# Современная фабрика сессий с типизацией
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,  # Ручное управление flush для лучшей производительности
)

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Типизированный контекстный менеджер для получения сессии БД"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db() -> None:
    """Инициализация БД с логированием"""
    logger.info("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully")



