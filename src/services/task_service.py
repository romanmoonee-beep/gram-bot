from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_session
from app.database.models.task import Task, TaskType, TaskStatus
from app.database.models.task_execution import TaskExecution, ExecutionStatus
from app.database.models.user import User, UserLevel
from app.database.models.transaction import Transaction, TransactionType
from app.services.user_service import UserService
from app.services.transaction_service import TransactionService
from app.config.settings import settings

logger = structlog.get_logger(__name__)

class TaskService:
    """Сервис для работы с заданиями"""
    
    def __init__(self):
        self.user_service = UserService()
        self.transaction_service = TransactionService()
    
    async def create_task(
        self,
        author_id: int,
        task_type: TaskType,
        title: str,
        description: str,
        target_url: str,
        reward_amount: Decimal,
        target_executions: int,
        expires_at: datetime | None = None,
        min_user_level: str | None = None,
        auto_check: bool = True
    ) -> Task | None:
        """Создать новое задание"""
        async with get_session() as session:
            # Получаем автора
            author = await self.user_service.get_user(author_id)
            if not author:
                logger.error("Author not found", author_id=author_id)
                return None
            
            # Рассчитываем бюджет
            user_config = author.get_level_config()
            commission_rate = user_config["commission_rate"]
            
            total_reward = reward_amount * target_executions
            commission = total_reward * commission_rate
            total_budget = total_reward + commission
            
            # Проверяем баланс
            if author.available_balance < total_budget:
                logger.warning(
                    "Insufficient balance for task creation",
                    author_id=author_id,
                    required=float(total_budget),
                    available=float(author.available_balance)
                )
                return None
            
            # Создаем задание
            task = Task(
                author_id=author_id,
                type=task_type,
                status=TaskStatus.ACTIVE,
                title=title,
                description=description,
                target_url=target_url,
                reward_amount=reward_amount,
                target_executions=target_executions,
                total_budget=total_budget,
                commission_amount=commission,
                expires_at=expires_at,
                min_user_level=min_user_level,
                auto_check=auto_check
            )
            
            session.add(task)
            await session.flush()  # Получаем ID
            
            # Замораживаем средства
            success = await self.user_service.freeze_balance(
                author_id,
                total_budget,
                f"Создание задания #{task.id}"
            )
            
            if not success:
                await session.rollback()
                return None
            
            # Создаем транзакцию списания
            await self.transaction_service.create_transaction(
                user_id=author_id,
                amount=-total_budget,
                transaction_type=TransactionType.TASK_CREATION,
                description=f"Создание задания: {title}",
                reference_id=str(task.id),
                reference_type="task",
                session=session
            )
            
            # Обновляем статистику автора
            author.tasks_created += 1
            author.daily_tasks_created += 1
            author.last_task_date = datetime.utcnow()
            
            await session.commit()
            await session.refresh(task)
            
            logger.info(
                "Task created successfully",
                task_id=task.id,
                author_id=author_id,
                type=task_type,
                reward=float(reward_amount),
                budget=float(total_budget)
            )
            
            return task
    
    async def get_available_tasks(
        self,
        user: User,
        task_type: TaskType | None = None,
        limit: int = 20,
        offset: int = 0
    ) -> list[Task]:
        """Получить доступные задания для пользователя"""
        async with get_session() as session:
            query = select(Task).where(
                and_(
                    Task.status == TaskStatus.ACTIVE,
                    Task.author_id != user.telegram_id,  # Не свои задания
                    Task.completed_executions < Task.target_executions,  # Не завершенные
                    or_(
                        Task.expires_at.is_(None),
                        Task.expires_at > datetime.utcnow()
                    )
                )
            )
            
            # Фильтр по типу
            if task_type:
                query = query.where(Task.type == task_type)
            
            # Фильтр по минимальному уровню
            if user.level in ["bronze", "silver", "gold", "premium"]:
                level_hierarchy = ["bronze", "silver", "gold", "premium"]
                user_level_index = level_hierarchy.index(user.level)
                
                query = query.where(
                    or_(
                        Task.min_user_level.is_(None),
                        Task.min_user_level.in_(level_hierarchy[:user_level_index + 1])
                    )
                )
            
            # Исключаем задания, которые пользователь уже выполнил
            executed_tasks_subquery = select(TaskExecution.task_id).where(
                TaskExecution.user_id == user.telegram_id
            )
            query = query.where(Task.id.not_in(executed_tasks_subquery))
            
            # Сортировка по награде (убывание)
            query = query.order_by(desc(Task.reward_amount))
            query = query.limit(limit).offset(offset)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def get_task_by_id(self, task_id: int) -> Task | None:
        """Получить задание по ID"""
        async with get_session() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            return result.scalar_one_or_none()
    
    async def execute_task(self, task_id: int, user_id: int) -> TaskExecution | None:
        """Начать выполнение задания"""
        async with get_session() as session:
            # Получаем задание
            task = await self.get_task_by_id(task_id)
            if not task or not task.is_active:
                return None
            
            # Проверяем, не выполнял ли уже пользователь это задание
            existing = await session.execute(
                select(TaskExecution).where(
                    and_(
                        TaskExecution.task_id == task_id,
                        TaskExecution.user_id == user_id
                    )
                )
            )
            
            if existing.scalar_one_or_none():
                logger.warning(
                    "User already executed this task",
                    task_id=task_id,
                    user_id=user_id
                )
                return None
            
            # Создаем выполнение
            execution = TaskExecution(
                task_id=task_id,
                user_id=user_id,
                status=ExecutionStatus.PENDING,
                reward_amount=task.reward_amount,
                started_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(seconds=settings.TASK_EXECUTION_TIMEOUT)
            )
            
            session.add(execution)
            await session.commit()
            await session.refresh(execution)
            
            logger.info(
                "Task execution started",
                task_id=task_id,
                user_id=user_id,
                execution_id=execution.id
            )
            
            return execution
    
    async def complete_task_execution(
        self,
        execution_id: int,
        auto_checked: bool = True,
        reviewer_id: int | None = None,
        review_comment: str | None = None
    ) -> bool:
        """Завершить выполнение задания"""
        async with get_session() as session:
            # Получаем выполнение
            result = await session.execute(
                select(TaskExecution).where(TaskExecution.id == execution_id)
            )
            execution = result.scalar_one_or_none()
            
            if not execution:
                return False
            
            if execution.status != ExecutionStatus.PENDING:
                logger.warning(
                    "Execution not in pending status",
                    execution_id=execution_id,
                    status=execution.status
                )
                return False
            
            # Получаем задание и пользователя
            task = await self.get_task_by_id(execution.task_id)
            user = await self.user_service.get_user(execution.user_id)
            
            if not task or not user:
                return False
            
            # Рассчитываем финальную награду с множителем уровня
            user_config = user.get_level_config()
            final_reward = execution.reward_amount * user_config["task_multiplier"]
            
            # Обновляем выполнение
            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.reviewed_at = datetime.utcnow()
            execution.auto_checked = auto_checked
            execution.reviewer_id = reviewer_id
            execution.review_comment = review_comment
            execution.reward_amount = final_reward
            
            # Начисляем награду пользователю
            await self.user_service.update_balance(
                execution.user_id,
                final_reward,
                TransactionType.TASK_REWARD,
                f"Награда за выполнение задания: {task.title}",
                str(task.id),
                "task"
            )
            
            # Обновляем статистику задания
            task.completed_executions += 1
            task.spent_budget += execution.reward_amount
            
            # Обновляем статистику пользователя
            user.tasks_completed += 1
            user.daily_tasks_completed += 1
            
            # Проверяем завершение задания
            if task.completed_executions >= task.target_executions:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.utcnow()
                
                # Возвращаем неиспользованные средства автору
                remaining_budget = task.remaining_budget
                if remaining_budget > 0:
                    await self.user_service.unfreeze_balance(
                        task.author_id,
                        remaining_budget,
                        f"Возврат неиспользованных средств задания #{task.id}"
                    )
            
            # Обрабатываем реферальные бонусы
            await self._process_referral_commission(user, final_reward, session)
            
            await session.commit()
            
            logger.info(
                "Task execution completed",
                execution_id=execution_id,
                task_id=task.id,
                user_id=user.telegram_id,
                reward=float(final_reward)
            )
            
            return True
    
    async def _process_referral_commission(
        self,
        user: User,
        reward_amount: Decimal,
        session: AsyncSession
    ) -> None:
        """Обработка реферальной комиссии"""
        if not user.referrer_id:
            return
        
        # Получаем реферера
        referrer = await self.user_service.get_user(user.referrer_id)
        if not referrer:
            return
        
        # Рассчитываем комиссию
        referrer_config = referrer.get_level_config()
        commission_rate = referrer_config["referral_rates"]["tasks"]
        commission = reward_amount * commission_rate
        
        # Начисляем комиссию
        await self.user_service.update_balance(
            referrer.telegram_id,
            commission,
            TransactionType.REFERRAL_COMMISSION,
            f"Комиссия с активности реферала @{user.username or user.telegram_id}",
            str(user.telegram_id),
            "referral"
        )
        
        # Обновляем статистику реферера
        referrer.referral_earnings += commission
        
        logger.info(
            "Referral commission processed",
            referrer_id=referrer.telegram_id,
            user_id=user.telegram_id,
            commission=float(commission)
        )
    
    async def get_user_tasks(
        self,
        author_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> list[Task]:
        """Получить задания пользователя"""
        async with get_session() as session:
            result = await session.execute(
                select(Task)
                .where(Task.author_id == author_id)
                .order_by(desc(Task.created_at))
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())
    
    async def get_user_executions(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> list[TaskExecution]:
        """Получить выполнения пользователя"""
        async with get_session() as session:
            result = await session.execute(
                select(TaskExecution)
                .where(TaskExecution.user_id == user_id)
                .order_by(desc(TaskExecution.created_at))
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())
    
    async def pause_task(self, task_id: int, author_id: int) -> bool:
        """Приостановить задание"""
        async with get_session() as session:
            result = await session.execute(
                select(Task).where(
                    and_(Task.id == task_id, Task.author_id == author_id)
                )
            )
            task = result.scalar_one_or_none()
            
            if not task or task.status != TaskStatus.ACTIVE:
                return False
            
            task.status = TaskStatus.PAUSED
            await session.commit()
            
            logger.info("Task paused", task_id=task_id, author_id=author_id)
            return True
    
    async def resume_task(self, task_id: int, author_id: int) -> bool:
        """Возобновить задание"""
        async with get_session() as session:
            result = await session.execute(
                select(Task).where(
                    and_(Task.id == task_id, Task.author_id == author_id)
                )
            )
            task = result.scalar_one_or_none()
            
            if not task or task.status != TaskStatus.PAUSED:
                return False
            
            task.status = TaskStatus.ACTIVE
            await session.commit()
            
            logger.info("Task resumed", task_id=task_id, author_id=author_id)
            return True
    
    async def cancel_task(self, task_id: int, author_id: int) -> bool:
        """Отменить задание"""
        async with get_session() as session:
            result = await session.execute(
                select(Task).where(
                    and_(Task.id == task_id, Task.author_id == author_id)
                )
            )
            task = result.scalar_one_or_none()
            
            if not task or task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                return False
            
            # Возвращаем замороженные средства
            remaining_budget = task.remaining_budget
            if remaining_budget > 0:
                await self.user_service.unfreeze_balance(
                    author_id,
                    remaining_budget,
                    f"Отмена задания #{task_id}"
                )
            
            task.status = TaskStatus.CANCELLED
            await session.commit()
            
            logger.info("Task cancelled", task_id=task_id, author_id=author_id)
            return True
    
    async def get_task_analytics(self, task_id: int) -> dict | None:
        """Получить аналитику задания"""
        async with get_session() as session:
            task = await self.get_task_by_id(task_id)
            if not task:
                return None
            
            # Статистика выполнений
            executions_stats = await session.execute(
                select(
                    TaskExecution.status,
                    func.count(TaskExecution.id).label('count')
                )
                .where(TaskExecution.task_id == task_id)
                .group_by(TaskExecution.status)
            )
            
            executions_by_status = {
                row.status: row.count for row in executions_stats
            }
            
            # Временная статистика
            timing_stats = await session.execute(
                select(
                    func.avg(
                        func.extract('epoch', TaskExecution.completed_at - TaskExecution.started_at)
                    ).label('avg_seconds'),
                    func.min(
                        func.extract('epoch', TaskExecution.completed_at - TaskExecution.started_at)
                    ).label('min_seconds'),
                    func.max(
                        func.extract('epoch', TaskExecution.completed_at - TaskExecution.started_at)
                    ).label('max_seconds')
                )
                .where(
                    and_(
                        TaskExecution.task_id == task_id,
                        TaskExecution.status == ExecutionStatus.COMPLETED,
                        TaskExecution.started_at.is_not(None),
                        TaskExecution.completed_at.is_not(None)
                    )
                )
            )
            
            timing = timing_stats.first()
            
            return {
                'task': task,
                'executions_by_status': executions_by_status,
                'completion_rate': (task.completed_executions / task.target_executions * 100) if task.target_executions > 0 else 0,
                'budget_utilization': {
                    'total': float(task.total_budget),
                    'spent': float(task.spent_budget),
                    'remaining': float(task.remaining_budget),
                    'utilization_percent': (task.spent_budget / task.total_budget * 100) if task.total_budget > 0 else 0
                },
                'timing': {
                    'average_seconds': float(timing.avg_seconds or 0),
                    'fastest_seconds': float(timing.min_seconds or 0),
                    'slowest_seconds': float(timing.max_seconds or 0)
                }
            }
