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
    from app.database.models.task import Task
    from app.database.models.user import User

class ExecutionStatus(StrEnum):
    """Статусы выполнения заданий"""
    PENDING = "pending"               # Ожидает проверки
    IN_PROGRESS = "in_progress"       # В процессе выполнения
    COMPLETED = "completed"           # Успешно выполнено
    REJECTED = "rejected"             # Отклонено
    EXPIRED = "expired"               # Истекло время
    CANCELLED = "cancelled"           # Отменено пользователем

class TaskExecution(Base):
    __tablename__ = "task_executions"
    
    # Основные поля
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        index=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True
    )
    
    # Статус и результат
    status: Mapped[ExecutionStatus] = mapped_column(
        String(20),
        default=ExecutionStatus.PENDING,
        index=True
    )
    reward_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        default=Decimal("0.00")
    )
    
    # Данные для проверки
    screenshot_url: Mapped[str | None] = mapped_column(String(500))
    proof_data: Mapped[str | None] = mapped_column(Text)  # JSON с доказательствами
    user_comment: Mapped[str | None] = mapped_column(Text)
    
    # Результаты проверки
    reviewer_id: Mapped[int | None] = mapped_column(BigInteger)
    review_comment: Mapped[str | None] = mapped_column(Text)
    auto_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Связи
    task: Mapped[Task] = relationship(lazy="selectin")
    user: Mapped[User] = relationship(lazy="selectin")
    
    # Составные индексы
    __table_args__ = (
        Index("ix_task_executions_task_user", "task_id", "user_id"),
        Index("ix_task_executions_status_created", "status", "created_at"),
        Index("ix_task_executions_user_status", "user_id", "status"),
        Index("ix_task_executions_reviewer", "reviewer_id", "reviewed_at"),
    )
    
    def __repr__(self) -> str:
        return f"<TaskExecution(id={self.id}, task_id={self.task_id}, user_id={self.user_id}, status={self.status})>"
