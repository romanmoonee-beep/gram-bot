from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Настройки приложения с полной поддержкой Telegram Stars"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # ==================== ОСНОВНЫЕ НАСТРОЙКИ ====================
    
    # Режим работы
    DEBUG: bool = Field(default=False, description="Режим отладки")
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Окружение приложения"
    )
    
    # ==================== TELEGRAM BOT ====================
    
    BOT_TOKEN: str = Field(description="Токен Telegram бота")
    BOT_USERNAME: str = Field(description="Username бота (без @)")
    WEBHOOK_URL: str | None = Field(default=None, description="URL для webhook")
    WEBHOOK_SECRET: str | None = Field(default=None, description="Секрет для webhook")
    
    # ==================== БАЗА ДАННЫХ ====================
    
    # PostgreSQL настройки
    DB_HOST: str = Field(default="localhost", description="Хост БД")
    DB_PORT: int = Field(default=5432, description="Порт БД")
    DB_USER: str = Field(default="postgres", description="Пользователь БД")
    DB_PASSWORD: str = Field(description="Пароль БД")
    DB_NAME: str = Field(default="prgram", description="Имя БД")
    
    # Дополнительные настройки БД
    DB_POOL_SIZE: int = Field(default=50, description="Размер пула соединений")
    DB_MAX_OVERFLOW: int = Field(default=100, description="Максимальное переполнение пула")
    DB_ECHO: bool = Field(default=False, description="Логирование SQL запросов")
    USE_PGBOUNCER: bool = Field(default=False, description="Использование PgBouncer")
    
    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """Автоматическая генерация URL БД"""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # ==================== REDIS ====================
    
    REDIS_HOST: str = Field(default="localhost", description="Хост Redis")
    REDIS_PORT: int = Field(default=6379, description="Порт Redis")
    REDIS_PASSWORD: str | None = Field(default=None, description="Пароль Redis")
    REDIS_DB: int = Field(default=0, description="Номер БД Redis")
    
    @computed_field
    @property
    def REDIS_URL(self) -> str:
        """Автоматическая генерация URL Redis"""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # ==================== TELEGRAM STARS НАСТРОЙКИ ====================
    
    # Курс обмена Stars -> GRAM
    STARS_TO_GRAM_BASE_RATE: int = Field(
        default=10, 
        description="Базовый курс: 1 Star = X GRAM"
    )
    
    # Пакеты для покупки с бонусами
    STARS_PACKAGES: dict[str, dict] = Field(
        default={
            "basic": {
                "stars": 100,
                "gram": 1000,
                "bonus_percent": 0,
                "title": "🌟 Базовый",
                "description": "100 Stars → 1,000 GRAM"
            },
            "economy": {
                "stars": 450,
                "gram": 5000,
                "bonus_percent": 10,
                "title": "💰 Экономия 10%",
                "description": "450 Stars → 5,000 GRAM"
            },
            "standard": {
                "stars": 850,
                "gram": 10000,
                "bonus_percent": 15,
                "title": "💰 Экономия 15%",
                "description": "850 Stars → 10,000 GRAM"
            },
            "premium": {
                "stars": 2000,
                "gram": 25000,
                "bonus_percent": 20,
                "bonus_gram": 1000,
                "title": "💰 Экономия 20% + Бонус!",
                "description": "2000 Stars → 25,000 GRAM + 1,000 бонус"
            }
        },
        description="Пакеты Stars для покупки"
    )
    
    # Минимальные суммы для операций
    MIN_DEPOSIT_STARS: int = Field(default=50, description="Минимум Stars для пополнения")
    MAX_DEPOSIT_STARS: int = Field(default=10000, description="Максимум Stars за раз")
    
    # ==================== УРОВНИ ПОЛЬЗОВАТЕЛЕЙ ====================
    
    # Пороги для уровней (в GRAM)
    LEVEL_THRESHOLDS: dict[str, Decimal] = Field(
        default={
            "bronze": Decimal("0"),
            "silver": Decimal("10000"),
            "gold": Decimal("50000"),
            "premium": Decimal("100000")
        },
        description="Пороги балансов для уровней"
    )
    
    # Комиссии по уровням (в процентах)
    LEVEL_COMMISSIONS: dict[str, Decimal] = Field(
        default={
            "bronze": Decimal("0.07"),    # 7%
            "silver": Decimal("0.06"),    # 6%
            "gold": Decimal("0.05"),      # 5%
            "premium": Decimal("0.03")    # 3%
        },
        description="Комиссии с заданий по уровням"
    )
    
    # Реферальные бонусы по уровням
    REFERRAL_BONUSES: dict[str, Decimal] = Field(
        default={
            "bronze": Decimal("1000"),
            "silver": Decimal("1500"),
            "gold": Decimal("2000"),
            "premium": Decimal("3000")
        },
        description="Бонусы за привлечение рефералов"
    )
    
    # Процент с активности рефералов
    REFERRAL_COMMISSION_RATES: dict[str, dict[str, Decimal]] = Field(
        default={
            "bronze": {"tasks": Decimal("0.05"), "deposits": Decimal("0.10")},
            "silver": {"tasks": Decimal("0.05"), "deposits": Decimal("0.10")},
            "gold": {"tasks": Decimal("0.05"), "deposits": Decimal("0.10")},
            "premium": {"tasks": Decimal("0.05"), "deposits": Decimal("0.10")}
        },
        description="Процент с активности рефералов (задания/пополнения)"
    )
    
    # ==================== ЛИМИТЫ И ОГРАНИЧЕНИЯ ====================
    
    # Дневные лимиты заданий по уровням
    DAILY_TASK_LIMITS: dict[str, int] = Field(
        default={
            "bronze": 5,
            "silver": 15,
            "gold": 30,
            "premium": -1  # Безлимит
        },
        description="Дневные лимиты создания заданий"
    )
    
    # Максимальные награды за задания по уровням
    MAX_TASK_REWARDS: dict[str, Decimal] = Field(
        default={
            "bronze": Decimal("500"),
            "silver": Decimal("1000"),
            "gold": Decimal("2000"),
            "premium": Decimal("5000")
        },
        description="Максимальные награды за задания"
    )
    
    # Минимальные суммы для операций
    MIN_TASK_REWARD: Decimal = Field(default=Decimal("50"), description="Минимальная награда за задание")
    MIN_CHECK_AMOUNT: Decimal = Field(default=Decimal("10"), description="Минимальная сумма чека")
    MAX_CHECK_AMOUNT: Decimal = Field(default=Decimal("100000"), description="Максимальная сумма чека")
    
    # ==================== АНТИФРОД НАСТРОЙКИ ====================
    
    # Лимиты для защиты от ботов
    MAX_ACTIONS_PER_MINUTE: int = Field(default=30, description="Максимум действий в минуту")
    MAX_TASKS_PER_HOUR: int = Field(default=10, description="Максимум заданий в час")
    SUSPICIOUS_ACTIVITY_THRESHOLD: int = Field(default=50, description="Порог подозрительной активности")
    
    # Время блокировок (в секундах)
    SPAM_BLOCK_DURATION: int = Field(default=3600, description="Время блокировки за спам (1 час)")
    FRAUD_BLOCK_DURATION: int = Field(default=86400, description="Время блокировки за фрод (24 часа)")
    
    # ==================== СИСТЕМА ЧЕКОВ ====================
    
    # Время жизни чеков (в секундах)
    CHECK_EXPIRY_TIME: int = Field(default=2592000, description="Время жизни чека (30 дней)")
    MAX_CHECK_ACTIVATIONS: int = Field(default=1000, description="Максимум активаций мульти-чека")
    
    # ==================== ЗАДАНИЯ ====================
    
    # Время на выполнение заданий (в секундах)
    TASK_EXECUTION_TIMEOUT: int = Field(default=1800, description="Таймаут выполнения задания (30 мин)")
    MANUAL_REVIEW_TIMEOUT: int = Field(default=86400, description="Таймаут ручной проверки (24 часа)")
    
    # Время ожидания между одинаковыми заданиями (в секундах)
    SAME_TASK_COOLDOWN: int = Field(default=300, description="Кулдаун между одинаковыми заданиями (5 мин)")
    
    # ==================== УВЕДОМЛЕНИЯ ====================
    
    # Настройки уведомлений
    NOTIFICATION_RATE_LIMIT: int = Field(default=10, description="Лимит уведомлений в минуту")
    BATCH_NOTIFICATION_SIZE: int = Field(default=100, description="Размер пакета уведомлений")
    
    # ==================== ЛОГИРОВАНИЕ ====================
    
    LOG_LEVEL: str = Field(default="INFO", description="Уровень логирования")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Формат логов"
    )
    SLOW_QUERY_THRESHOLD: float = Field(default=0.5, description="Порог медленных запросов (сек)")
    
    # ==================== ВНЕШНИЕ СЕРВИСЫ ====================
    
    # Мониторинг
    SENTRY_DSN: str | None = Field(default=None, description="Sentry DSN для мониторинга ошибок")
    
    # Метрики
    PROMETHEUS_PORT: int = Field(default=8000, description="Порт для метрик Prometheus")
    METRICS_ENABLED: bool = Field(default=True, description="Включить сбор метрик")
    
    # ==================== БЕЗОПАСНОСТЬ ====================
    
    # JWT настройки (если будет веб-интерфейс)
    SECRET_KEY: str = Field(description="Секретный ключ для подписи токенов")
    ALGORITHM: str = Field(default="HS256", description="Алгоритм подписи")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Время жизни токена доступа")
    
    # Админы бота
    ADMIN_IDS: list[int] = Field(default=[], description="ID администраторов бота")
    
    # ==================== ВАЛИДАТОРЫ ====================
    
    @field_validator("BOT_TOKEN")
    @classmethod
    def validate_bot_token(cls, v: str) -> str:
        if not v or not v.count(":") == 1:
            raise ValueError("Неверный формат токена бота")
        return v
    
    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v
    
    # ==================== ВЫЧИСЛЯЕМЫЕ ПОЛЯ ====================
    
    @computed_field
    @property
    def is_production(self) -> bool:
        """Проверка продакшн окружения"""
        return self.ENVIRONMENT == "production"
    
    @computed_field
    @property
    def base_url(self) -> str:
        """Базовый URL для webhook"""
        return self.WEBHOOK_URL.rstrip("/") if self.WEBHOOK_URL else ""
    
    # ==================== МЕТОДЫ РАБОТЫ С НАСТРОЙКАМИ ====================
    
    def get_stars_package(self, package_name: str) -> dict | None:
        """Получить конфигурацию пакета Stars"""
        return self.STARS_PACKAGES.get(package_name)
    
    def calculate_gram_from_stars(self, stars: int, package_name: str | None = None) -> tuple[Decimal, Decimal]:
        """
        Рассчитать количество GRAM из Stars
        Возвращает: (основная_сумма, бонус)
        """
        if package_name and package_name in self.STARS_PACKAGES:
            package = self.STARS_PACKAGES[package_name]
            if stars == package["stars"]:
                base_gram = Decimal(str(package["gram"]))
                bonus_gram = Decimal(str(package.get("bonus_gram", 0)))
                return base_gram, bonus_gram
        
        # Стандартный расчет
        base_gram = Decimal(str(stars * self.STARS_TO_GRAM_BASE_RATE))
        return base_gram, Decimal("0")
    
    def get_user_level_config(self, level: str) -> dict:
        """Получить полную конфигурацию уровня пользователя"""
        return {
            "threshold": self.LEVEL_THRESHOLDS.get(level, Decimal("0")),
            "commission": self.LEVEL_COMMISSIONS.get(level, Decimal("0.07")),
            "referral_bonus": self.REFERRAL_BONUSES.get(level, Decimal("1000")),
            "daily_task_limit": self.DAILY_TASK_LIMITS.get(level, 5),
            "max_task_reward": self.MAX_TASK_REWARDS.get(level, Decimal("500")),
            "referral_rates": self.REFERRAL_COMMISSION_RATES.get(level, {
                "tasks": Decimal("0.05"),
                "deposits": Decimal("0.10")
            })
        }
    
    def is_admin(self, user_id: int) -> bool:
        """Проверить, является ли пользователь администратором"""
        return user_id in self.ADMIN_IDS
    
    # ==================== JSON СЕРИАЛИЗАЦИЯ ====================
    
    @staticmethod
    def json_dumps(obj) -> str:
        """Кастомная JSON сериализация с поддержкой Decimal"""
        def decimal_serializer(o):
            if isinstance(o, Decimal):
                return float(o)
            raise TypeError(f"Object of type {type(o)} is not JSON serializable")
        
        return json.dumps(obj, default=decimal_serializer, ensure_ascii=False)
    
    @staticmethod
    def json_loads(s: str):
        """Кастомная JSON десериализация"""
        return json.loads(s)

# Создаем глобальный экземпляр настроек
settings = Settings()

