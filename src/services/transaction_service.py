from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_session
from app.database.models.transaction import Transaction, TransactionType, TransactionStatus
from app.database.models.user import User
from app.config.settings import settings

logger = structlog.get_logger(__name__)

class TransactionService:
    """Сервис для работы с транзакциями"""
    
    async def create_transaction(
        self,
        user_id: int,
        amount: Decimal,
        transaction_type: TransactionType,
        description: str = "",
        reference_id: str | None = None,
        reference_type: str | None = None,
        stars_amount: int | None = None,
        stars_transaction_id: str | None = None,
        status: TransactionStatus = TransactionStatus.COMPLETED,
        session: AsyncSession | None = None
    ) -> Transaction:
        """Создать новую транзакцию"""
        
        async def _create_in_session(session: AsyncSession) -> Transaction:
            # Получаем текущий баланс пользователя
            result = await session.execute(
                select(User.balance).where(User.telegram_id == user_id)
            )
            current_balance = result.scalar_one_or_none()
            
            if current_balance is None:
                raise ValueError(f"User {user_id} not found")
            
            # Создаем транзакцию
            transaction = Transaction(
                user_id=user_id,
                type=transaction_type,
                status=status,
                amount=amount,
                description=description,
                reference_id=reference_id,
                reference_type=reference_type,
                stars_amount=stars_amount,
                stars_transaction_id=stars_transaction_id,
                balance_before=current_balance,
                balance_after=current_balance + amount if status == TransactionStatus.COMPLETED else current_balance,
                created_at=datetime.utcnow()
            )
            
            session.add(transaction)
            await session.commit()
            await session.refresh(transaction)
            
            logger.info(
                "💳 Transaction created",
                transaction_id=transaction.id,
                user_id=user_id,
                type=transaction_type,
                amount=float(amount),
                status=status
            )
            
            return transaction
        
        if session:
            return await _create_in_session(session)
        else:
            async with get_session() as session:
                return await _create_in_session(session)
    
    async def get_user_transactions(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        transaction_type: TransactionType | None = None
    ) -> list[Transaction]:
        """Получить транзакции пользователя"""
        async with get_session() as session:
            query = select(Transaction).where(Transaction.user_id == user_id)
            
            if transaction_type:
                query = query.where(Transaction.type == transaction_type)
            
            query = query.order_by(desc(Transaction.created_at)).limit(limit).offset(offset)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def get_transaction_by_id(self, transaction_id: int) -> Transaction | None:
        """Получить транзакцию по ID"""
        async with get_session() as session:
            result = await session.execute(
                select(Transaction).where(Transaction.id == transaction_id)
            )
            return result.scalar_one_or_none()
    
    async def get_transaction_by_stars_id(self, stars_transaction_id: str) -> Transaction | None:
        """Получить транзакцию по ID Telegram Stars"""
        async with get_session() as session:
            result = await session.execute(
                select(Transaction).where(Transaction.stars_transaction_id == stars_transaction_id)
            )
            return result.scalar_one_or_none()
    
    async def update_transaction_status(
        self,
        transaction_id: int,
        status: TransactionStatus,
        processed_at: datetime | None = None
    ) -> bool:
        """Обновить статус транзакции"""
        async with get_session() as session:
            result = await session.execute(
                select(Transaction).where(Transaction.id == transaction_id)
            )
            transaction = result.scalar_one_or_none()
            
            if not transaction:
                return False
            
            transaction.status = status
            transaction.processed_at = processed_at or datetime.utcnow()
            
            await session.commit()
            
            logger.info(
                "🔄 Transaction status updated",
                transaction_id=transaction_id,
                new_status=status
            )
            
            return True
    
    async def get_user_transaction_stats(self, user_id: int) -> dict:
        """Получить статистику транзакций пользователя"""
        async with get_session() as session:
            # Общая статистика
            total_stats = await session.execute(
                select(
                    func.count(Transaction.id).label('total_count'),
                    func.sum(Transaction.amount).filter(Transaction.amount > 0).label('total_income'),
                    func.sum(Transaction.amount).filter(Transaction.amount < 0).label('total_spending')
                )
                .where(Transaction.user_id == user_id)
                .where(Transaction.status == TransactionStatus.COMPLETED)
            )
            
            stats = total_stats.first()
            
            # Статистика по типам
            type_stats = await session.execute(
                select(
                    Transaction.type,
                    func.count(Transaction.id).label('count'),
                    func.sum(Transaction.amount).label('total_amount')
                )
                .where(Transaction.user_id == user_id)
                .where(Transaction.status == TransactionStatus.COMPLETED)
                .group_by(Transaction.type)
            )
            
            # Статистика за последние 30 дней
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_stats = await session.execute(
                select(
                    func.count(Transaction.id).label('recent_count'),
                    func.sum(Transaction.amount).filter(Transaction.amount > 0).label('recent_income'),
                    func.sum(Transaction.amount).filter(Transaction.amount < 0).label('recent_spending')
                )
                .where(Transaction.user_id == user_id)
                .where(Transaction.status == TransactionStatus.COMPLETED)
                .where(Transaction.created_at >= thirty_days_ago)
            )
            
            recent = recent_stats.first()
            
            return {
                'total': {
                    'count': stats.total_count or 0,
                    'income': float(stats.total_income or 0),
                    'spending': float(abs(stats.total_spending or 0))
                },
                'recent_30_days': {
                    'count': recent.recent_count or 0,
                    'income': float(recent.recent_income or 0),
                    'spending': float(abs(recent.recent_spending or 0))
                },
                'by_type': {
                    row.type: {
                        'count': row.count,
                        'total_amount': float(row.total_amount)
                    }
                    for row in type_stats
                }
            }
    
    async def process_telegram_stars_payment(
        self,
        user_id: int,
        stars_amount: int,
        stars_transaction_id: str,
        package_name: str | None = None
    ) -> Transaction | None:
        """Обработать платеж через Telegram Stars"""
        
        # Проверяем, не обработан ли уже этот платеж
        existing = await self.get_transaction_by_stars_id(stars_transaction_id)
        if existing:
            logger.warning(
                "⚠️ Duplicate stars payment attempt",
                user_id=user_id,
                stars_transaction_id=stars_transaction_id
            )
            return existing
        
        # Рассчитываем количество GRAM
        base_gram, bonus_gram = settings.calculate_gram_from_stars(stars_amount, package_name)
        total_gram = base_gram + bonus_gram
        
        async with get_session() as session:
            # Создаем основную транзакцию
            main_transaction = await self.create_transaction(
                user_id=user_id,
                amount=base_gram,
                transaction_type=TransactionType.DEPOSIT_STARS,
                description=f"Пополнение через Telegram Stars: {stars_amount} ⭐ → {base_gram} GRAM",
                stars_amount=stars_amount,
                stars_transaction_id=stars_transaction_id,
                session=session
            )
            
            # Создаем бонусную транзакцию если есть бонус
            if bonus_gram > 0:
                await self.create_transaction(
                    user_id=user_id,
                    amount=bonus_gram,
                    transaction_type=TransactionType.DEPOSIT_BONUS,
                    description=f"Бонус к пополнению: +{bonus_gram} GRAM",
                    reference_id=str(main_transaction.id),
                    reference_type="deposit",
                    session=session
                )
            
            # Обновляем баланс пользователя
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                user.balance += total_gram
                user.total_deposited += total_gram
                await session.commit()
            
            logger.info(
                "⭐ Stars payment processed",
                user_id=user_id,
                stars_amount=stars_amount,
                gram_amount=float(total_gram),
                bonus_gram=float(bonus_gram),
                package=package_name
            )
            
            return main_transaction
    
    async def get_daily_transaction_volume(self, date: datetime | None = None) -> dict:
        """Получить дневной объем транзакций"""
        if not date:
            date = datetime.utcnow()
        
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        async with get_session() as session:
            result = await session.execute(
                select(
                    Transaction.type,
                    func.count(Transaction.id).label('count'),
                    func.sum(Transaction.amount).label('total_amount')
                )
                .where(Transaction.created_at >= start_of_day)
                .where(Transaction.created_at < end_of_day)
                .where(Transaction.status == TransactionStatus.COMPLETED)
                .group_by(Transaction.type)
            )
            
            volume_by_type = {}
            total_volume = Decimal('0')
            total_count = 0
            
            for row in result:
                volume_by_type[row.type] = {
                    'count': row.count,
                    'amount': float(row.total_amount)
                }
                total_volume += row.total_amount
                total_count += row.count
            
            return {
                'date': date.strftime('%Y-%m-%d'),
                'total_count': total_count,
                'total_volume': float(total_volume),
                'by_type': volume_by_type
            }
    
    async def get_pending_transactions(self, limit: int = 100) -> list[Transaction]:
        """Получить транзакции в ожидании обработки"""
        async with get_session() as session:
            result = await session.execute(
                select(Transaction)
                .where(Transaction.status == TransactionStatus.PENDING)
                .order_by(Transaction.created_at)
                .limit(limit)
            )
            return list(result.scalars().all())
    
    async def cancel_transaction(
        self,
        transaction_id: int,
        reason: str = ""
    ) -> bool:
        """Отменить транзакцию"""
        async with get_session() as session:
            result = await session.execute(
                select(Transaction).where(Transaction.id == transaction_id)
            )
            transaction = result.scalar_one_or_none()
            
            if not transaction:
                return False
            
            if transaction.status != TransactionStatus.PENDING:
                logger.warning(
                    "⚠️ Cannot cancel non-pending transaction",
                    transaction_id=transaction_id,
                    current_status=transaction.status
                )
                return False
            
            transaction.status = TransactionStatus.CANCELLED
            transaction.description += f" | Отменено: {reason}" if reason else " | Отменено"
            transaction.processed_at = datetime.utcnow()
            
            await session.commit()
            
            logger.info(
                "❌ Transaction cancelled",
                transaction_id=transaction_id,
                reason=reason
            )
            
            return True