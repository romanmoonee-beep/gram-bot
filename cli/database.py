# app/cli/database.py - CLI команды для управления БД
# ==============================================================================

import asyncio
import sys
from pathlib import Path

import typer
from alembic import command
from alembic.config import Config
from sqlalchemy import text

app = typer.Typer(help="Команды для управления базой данных")

# Добавляем корень проекта в Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.config.settings import settings
from app.database.database import engine, init_db

def get_alembic_config() -> Config:
    """Получить конфигурацию Alembic"""
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("+asyncpg", ""))
    return alembic_cfg

@app.command()
def init():
    """Инициализация базы данных"""
    typer.echo("🔧 Инициализация базы данных...")
    
    async def _init():
        await init_db()
        typer.echo("✅ База данных инициализирована!")
    
    asyncio.run(_init())

@app.command()
def migrate(message: str = typer.Argument(..., help="Сообщение для миграции")):
    """Создать новую миграцию"""
    typer.echo(f"📝 Создание миграции: {message}")
    
    alembic_cfg = get_alembic_config()
    command.revision(alembic_cfg, autogenerate=True, message=message)
    
    typer.echo("✅ Миграция создана!")

@app.command()
def upgrade(revision: str = "head"):
    """Применить миграции"""
    typer.echo(f"⬆️ Применение миграций до {revision}")
    
    alembic_cfg = get_alembic_config()
    command.upgrade(alembic_cfg, revision)
    
    typer.echo("✅ Миграции применены!")

@app.command()
def downgrade(revision: str = "-1"):
    """Откатить миграции"""
    typer.echo(f"⬇️ Откат миграций до {revision}")
    
    alembic_cfg = get_alembic_config()
    command.downgrade(alembic_cfg, revision)
    
    typer.echo("✅ Миграции откачены!")

@app.command()
def reset(force: bool = typer.Option(False, "--force", help="Принудительный сброс без подтверждения")):
    """Сброс базы данных (ВНИМАНИЕ: удаляет все данные!)"""
    if not force:
        confirm = typer.confirm("⚠️ Это удалит ВСЕ данные в базе! Продолжить?")
        if not confirm:
            typer.echo("❌ Отменено")
            return
    
    async def _reset():
        async with engine.begin() as conn:
            # Удаляем все таблицы
            await conn.run_sync(lambda sync_conn: 
                sync_conn.execute(text("DROP SCHEMA public CASCADE"))
            )
            await conn.run_sync(lambda sync_conn: 
                sync_conn.execute(text("CREATE SCHEMA public"))
            )
            await conn.run_sync(lambda sync_conn: 
                sync_conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
            )
            await conn.run_sync(lambda sync_conn: 
                sync_conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
            )
        
        typer.echo("🗑️ База данных очищена")
        
        # Применяем миграции
        alembic_cfg = get_alembic_config()
        command.upgrade(alembic_cfg, "head")
        
        typer.echo("✅ База данных пересоздана!")
    
    asyncio.run(_reset())

@app.command()
def seed():
    """Заполнить БД тестовыми данными"""
    typer.echo("🌱 Заполнение тестовыми данными...")
    
    async def _seed():
        from app.database.models.user import User, UserLevel
        from app.database.models.transaction import Transaction, TransactionType
        from app.database.database import get_session
        from decimal import Decimal
        
        async with get_session() as session:
            # Создаем тестового администратора
            admin = User(
                telegram_id=123456789,
                username="admin",
                first_name="Admin",
                balance=Decimal("1000000.00"),
                level=UserLevel.PREMIUM,
                is_premium=True
            )
            session.add(admin)
            
            # Создаем тестовых пользователей
            users_data = [
                {"telegram_id": 111111111, "username": "test_bronze", "level": UserLevel.BRONZE, "balance": Decimal("5000.00")},
                {"telegram_id": 222222222, "username": "test_silver", "level": UserLevel.SILVER, "balance": Decimal("15000.00")},
                {"telegram_id": 333333333, "username": "test_gold", "level": UserLevel.GOLD, "balance": Decimal("75000.00")},
                {"telegram_id": 444444444, "username": "test_premium", "level": UserLevel.PREMIUM, "balance": Decimal("150000.00"), "is_premium": True},
            ]
            
            for user_data in users_data:
                user = User(**user_data)
                session.add(user)
            
            await session.commit()
            
            typer.echo("✅ Тестовые данные добавлены!")
            typer.echo("👤 Админ: @admin (ID: 123456789)")
            typer.echo("👤 Тестовые пользователи: @test_bronze, @test_silver, @test_gold, @test_premium")
    
    asyncio.run(_seed())

@app.command()
def status():
    """Показать статус базы данных"""
    async def _status():
        try:
            async with engine.begin() as conn:
                # Проверяем подключение
                result = await conn.execute(text("SELECT version()"))
                version = result.scalar()
                
                typer.echo("✅ Подключение к БД успешно")
                typer.echo(f"📊 Версия PostgreSQL: {version}")
                
                # Показываем количество таблиц
                result = await conn.execute(text("""
                    SELECT count(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                tables_count = result.scalar()
                typer.echo(f"📋 Количество таблиц: {tables_count}")
                
                # Показываем статистику пользователей
                if tables_count > 0:
                    result = await conn.execute(text("SELECT count(*) FROM users"))
                    users_count = result.scalar()
                    typer.echo(f"👥 Пользователей в системе: {users_count}")
                    
                    result = await conn.execute(text("SELECT count(*) FROM tasks"))
                    tasks_count = result.scalar()
                    typer.echo(f"📋 Заданий создано: {tasks_count}")
                    
                    result = await conn.execute(text("SELECT count(*) FROM transactions"))
                    transactions_count = result.scalar()
                    typer.echo(f"💰 Транзакций: {transactions_count}")
                
        except Exception as e:
            typer.echo(f"❌ Ошибка подключения к БД: {e}")
            sys.exit(1)
    
    asyncio.run(_status())

if __name__ == "__main__":
    app()