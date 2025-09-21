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

class CheckType(StrEnum):
    """Типы чеков"""
    PERSONAL = "personal"      # Персональный чек
    MULTI = "multi"           # Мульти-чек
    GIVEAWAY = "giveaway"     # Розыгрыш

class CheckStatus(StrEnum):
    """Статусы чеков"""
    ACTIVE = "active"         # Активный
    EXPIRED = "expired"       # Истек
    COMPLETED = "completed"   # Завершен (все активации использованы)
    CANCELLED = "cancelled"   # Отменен

class Check(Base):
    __tablename__ = "checks"
    
    # Основные поля
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    creator_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True
    )
    
    # Тип и статус
    type: Mapped[CheckType] = mapped_column(String(20), index=True)
    status: Mapped[CheckStatus] = mapped_column(
        String(20),
        default=CheckStatus.ACTIVE,
        index=True
    )
    
    # Финансовые параметры
    total_amount: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2))
    amount_per_activation: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2))
    
    # Параметры активации
    max_activations: Mapped[int] = mapped_column(Integer, default=1)
    current_activations: Mapped[int] = mapped_column(Integer, default=0)
    max_per_user: Mapped[int] = mapped_column(Integer, default=1)
    
    # Уникальный код чека
    check_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    
    # Дополнительные настройки
    title: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    password: Mapped[str | None] = mapped_column(String(100))
    
    # Условия получения
    required_subscription_channel: Mapped[str | None] = mapped_column(String(100))
    min_user_level: Mapped[str | None] = mapped_column(String(20))
    
    # Изображение чека
    image_url: Mapped[str | None] = mapped_column(String(500))
    
    # Временные ограничения
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
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
    
    # Связи
    creator: Mapped[User] = relationship(lazy="selectin")
    activations: Mapped[list[CheckActivation]] = relationship(
        back_populates="check",
        cascade="all, delete-orphan"
    )
    
    # Составные индексы
    __table_args__ = (
        Index("ix_checks_creator_status", "creator_id", "status"),
        Index("ix_checks_type_status", "type", "status"),
        Index("ix_checks_expires", "expires_at", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<Check(id={self.id}, code={self.check_code}, amount={self.total_amount})>"
    
    @property
    def is_active(self) -> bool:
        """Проверка активности чека"""
        if self.status != CheckStatus.ACTIVE:
            return False
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        
        if self.current_activations >= self.max_activations:
            return False
        
        if self.remaining_amount <= 0:
            return False
        
        return True
    
    @property
    def remaining_activations(self) -> int:
        """Оставшиеся активации"""
        return max(0, self.max_activations - self.current_activations)

class CheckActivation(Base):
    __tablename__ = "check_activations"
    
    # Основные поля
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    check_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("checks.id", ondelete="CASCADE"),
        index=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True
    )
    
    # Детали активации
    amount_received: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))
    transaction_id: Mapped[int | None] = mapped_column(Integer)
    
    # Временные метки
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )
    
    # Связи
    check: Mapped[Check] = relationship(back_populates="activations")
    user: Mapped[User] = relationship(lazy="selectin")
    
    # Составные индексы
    __table_args__ = (
        Index("ix_check_activations_check_user", "check_id", "user_id"),
        Index("ix_check_activations_user_activated", "user_id", "activated_at"),
    )
    
    def __repr__(self) -> str:
        return f"<CheckActivation(id={self.id}, check_id={self.check_id}, user_id={self.user_id})>"
