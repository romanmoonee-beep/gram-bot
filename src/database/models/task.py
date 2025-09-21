from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base

if TYPE_CHECKING:
    from app.database.models.user import User

class TaskType(StrEnum):
    """Типы заданий"""
    CHANNEL_SUBSCRIPTION = "channel_subscription"  # Подписка на канал
    GROUP_JOIN = "group_join"                     # Вступление в группу
    POST_VIEW = "post_view"                       # Просмотр поста
    POST_REACTION = "post_reaction"               # Реакция на пост
    BOT_INTERACTION = "bot_interaction"           # Взаимодействие с ботом
    CUSTOM = "custom"                             # Кастомное задание

class TaskStatus(StrEnum):
    """Статусы заданий"""
    DRAFT = "draft"           # Черновик
    ACTIVE = "active"         # Активное
    PAUSED = "paused"         # Приостановлено
    COMPLETED = "completed"   # Завершено
    CANCELLED = "cancelled"   # Отменено
    EXPIRED = "expired"       # Истекло

class Task(Base):
    __tablename__ = "tasks"
    
    # Основные поля
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    author_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True
    )
    
    # Тип и статус
    type: Mapped[TaskType] = mapped_column(String(50), index=True)
    status: Mapped[TaskStatus] = mapped_column(
        String(20),
        default=TaskStatus.DRAFT,
        index=True
    )
    
    # Основная информация
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    target_url: Mapped[str] = mapped_column(String(500))
    
    # Финансовые параметры
    reward_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        index=True
    )
    total_budget: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2))
    spent_budget: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        default=Decimal("0.00")
    )
    commission_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        default=Decimal("0.00")
    )
    
    # Параметры выполнения
    target_executions: Mapped[int] = mapped_column(Integer, default=1)
    completed_executions: Mapped[int] = mapped_column(Integer, default=0)
    max_executions_per_user: Mapped[int] = mapped_column(Integer, default=1)
    
    # Настройки проверки
    auto_check: Mapped[bool] = mapped_column(Boolean, default=True)
    manual_review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    check_delay_seconds: Mapped[int] = mapped_column(Integer, default=30)
    
    # Дополнительные условия
    required_subscription_channels: Mapped[str | None] = mapped_column(Text)  # JSON список
    min_user_level: Mapped[str | None] = mapped_column(String(20))
    geo_restrictions: Mapped[str | None] = mapped_column(Text)  # JSON список стран
    
    # Временные ограничения
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Метрики и аналитика
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    clicks_count: Mapped[int] = mapped_column(Integer, default=0)
    conversion_rate: Mapped[Decimal] = mapped_column(
        Numeric(precision=5, scale=2),
        default=Decimal("0.00")
    )
    
    # Связи
    author: Mapped[User] = relationship(
        back_populates="created_tasks",
        foreign_keys=[author_id],
        lazy="selectin"
    )
    
    # Составные индексы
    __table_args__ = (
        Index("ix_tasks_status_type", "status", "type"),
        Index("ix_tasks_author_status", "author_id", "status"),
        Index("ix_tasks_reward_created", "reward_amount", "created_at"),
        Index("ix_tasks_active_expires", "status", "expires_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', status={self.status})>"
    
    @property
    def is_active(self) -> bool:
        """Проверка активности задания"""
        if self.status != TaskStatus.ACTIVE:
            return False
        
        now = datetime.now()
        
        # Проверка времени начала
        if self.starts_at and now < self.starts_at:
            return False
        
        # Проверка времени окончания
        if self.expires_at and now > self.expires_at:
            return False
        
        # Проверка выполнения
        if self.completed_executions >= self.target_executions:
            return False
        
        return True
    
    @property
    def remaining_budget(self) -> Decimal:
        """Оставшийся бюджет"""
        return self.total_budget - self.spent_budget
    
    @property
    def remaining_executions(self) -> int:
        """Оставшееся количество выполнений"""
        return max(0, self.target_executions - self.completed_executions)
    
    @property
    def completion_percentage(self) -> Decimal:
        """Процент выполнения задания"""
        if self.target_executions == 0:
            return Decimal("100.00")
        return Decimal(str(self.completed_executions / self.target_executions * 100)).quantize(Decimal("0.01"))
    
    def can_be_executed_by_user(self, user_level: str) -> bool:
        """Проверка возможности выполнения задания пользователем"""
        if not self.is_active:
            return False
        
        # Проверка минимального уровня
        if self.min_user_level:
            level_hierarchy = ["bronze", "silver", "gold", "premium"]
            if user_level not in level_hierarchy:
                return False
            
            required_index = level_hierarchy.index(self.min_user_level)
            user_index = level_hierarchy.index(user_level)
            
            if user_index < required_index:
                return False
        
        return True