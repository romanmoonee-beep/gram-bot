from alembic.config import Config
from pathlib import Path

def get_alembic_config() -> Config:
    """Создание конфигурации Alembic"""
    # Путь к файлу alembic.ini
    ini_path = Path(__file__).parent.parent.parent / "alembic.ini"
    
    # Создаем конфигурацию
    alembic_cfg = Config(str(ini_path))
    
    # Устанавливаем URL БД из настроек
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("+asyncpg", ""))
    
    return alembic_cfg
