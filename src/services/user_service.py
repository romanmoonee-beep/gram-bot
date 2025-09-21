from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_session
from app.database.models.user import User, UserLevel
from app.database.models.transaction import Transaction, TransactionType, TransactionStatus
from app.config.settings import settings

logger = structlog.get_logger(__name__)

class UserService:
    """Сервис для работы с пользователями"""
    
    async def get_user(self, telegram_id: int) -> User | None:
        """Получить пользователя по Telegram ID"""
        async with get_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
    
    async def get_or_create_user(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        referrer_id: int | None = None
    ) -> User:
        """Получить существующего или создать нового пользователя"""
        async with get_session() as session:
            # Пытаемся найти существующего пользователя
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Обновляем информацию если изменилась
                updated = False
                if username and user.username != username:
                    user.username = username
                    updated = True
                if first_name and user.first_name != first_name:
                    user.first_name = first_name
                    updated = True
                if last_name and user.last_name != last_name:
                    user.last_name = last_name
                    updated = True
                
                if updated:
                    await session.commit()
                    await session.refresh(user)
                    
                return user
            
            # Создаем нового пользователя
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                referrer_id=referrer_id,
                balance=Decimal("0.00"),
                level=UserLevel.BRONZE
            )
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            logger.info(
                "👤 New user registered",
                telegram_id=telegram_id,
                username=username,
                referrer_id=referrer_id
            )
            
            # Обрабатываем реферальную систему
            if referrer_id:
                await self._process_referral_registration(user, referrer_id, session)
            
            return user
    
    async def _process_referral_registration(
        self, 
        new_user: User, 
        referrer_id: int, 
        session: AsyncSession
    ) -> None:
        """Обработка регистрации по реферальной ссылке"""
        # Находим реферера
        result = await session.execute(
            select(User).where(User.telegram_id == referrer_id)
        )
        referrer = result.scalar_one_or_none()
        
        if not referrer:
            logger.warning(
                "❌ Referrer not found",
                referrer_id=referrer_id,
                new_user_id=new_user.telegram_id
            )
            return
        
        # Увеличиваем счетчик рефералов
        referrer.total_referrals += 1
        if new_user.is_premium:
            referrer.premium_referrals += 1
        
        # Определяем бонус за реферала
        referrer_config = referrer.get_level_config()
        bonus = referrer_config["referral_bonus"]
        
        # Начисляем бонус
        referrer.balance += bonus
        referrer.referral_earnings += bonus
        
        # Создаем транзакцию
        transaction = Transaction(
            user_id=referrer.telegram_id,
            type=TransactionType.REFERRAL_BONUS,
            status=TransactionStatus.COMPLETED,
            amount=bonus,
            description=f"Бонус за реферала @{new_user.username or new_user.telegram_id}",
            balance_before=referrer.balance - bonus,
            balance_after=referrer.balance
        )
        
        session.add(transaction)
        await session.commit()
        
        logger.info(
            "🎉 Referral bonus processed",
            referrer_id=referrer.telegram_id,
            new_user_id=new_user.telegram_id,
            bonus=float(bonus)
        )
    
    async def update_balance(
        self,
        telegram_id: int,
        amount: Decimal,
        transaction_type: TransactionType,
        description: str = "",
        reference_id: str | None = None,
        reference_type: str | None = None
    ) -> bool:
        """Обновление баланса пользователя с созданием транзакции"""
        async with get_session() as session:
            # Получаем пользователя
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.error("❌ User not found for balance update", telegram_id=telegram_id)
                return False
            
            # Проверяем, что баланс не уйдет в минус
            new_balance = user.balance + amount
            if new_balance < 0:
                logger.warning(
                    "❌ Insufficient balance",
                    telegram_id=telegram_id,
                    current_balance=float(user.balance),
                    amount=float(amount)
                )
                return False
            
            # Сохраняем баланс до изменения
            balance_before = user.balance
            
            # Обновляем баланс
            user.balance = new_balance
            
            # Обновляем статистику
            if amount > 0:
                if transaction_type in [TransactionType.TASK_REWARD, TransactionType.REFERRAL_BONUS]:
                    user.total_earned += amount
                elif transaction_type == TransactionType.DEPOSIT_STARS:
                    user.total_deposited += amount
            else:
                user.total_spent += abs(amount)
            
            # Проверяем и обновляем уровень
            old_level = user.level
            new_level = self._calculate_user_level(user.balance, user.is_premium)
            if new_level != old_level:
                user.level = new_level
                logger.info(
                    "⬆️ User level upgraded",
                    telegram_id=telegram_id,
                    old_level=old_level,
                    new_level=new_level
                )
            
            # Создаем транзакцию
            transaction = Transaction(
                user_id=telegram_id,
                type=transaction_type,
                status=TransactionStatus.COMPLETED,
                amount=amount,
                description=description,
                reference_id=reference_id,
                reference_type=reference_type,
                balance_before=balance_before,
                balance_after=new_balance
            )
            
            session.add(transaction)
            await session.commit()
            
            logger.info(
                "💰 Balance updated",
                telegram_id=telegram_id,
                amount=float(amount),
                new_balance=float(new_balance),
                transaction_type=transaction_type
            )
            
            return True
    
    async def freeze_balance(
        self,
        telegram_id: int,
        amount: Decimal,
        description: str = ""
    ) -> bool:
        """Заморозка части баланса"""
        async with get_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            # Проверяем доступность средств
            if user.available_balance < amount:
                logger.warning(
                    "❌ Insufficient available balance for freeze",
                    telegram_id=telegram_id,
                    available=float(user.available_balance),
                    amount=float(amount)
                )
                return False
            
            # Замораживаем средства
            user.frozen_balance += amount
            
            # Создаем транзакцию
            transaction = Transaction(
                user_id=telegram_id,
                type=TransactionType.BALANCE_FREEZE,
                status=TransactionStatus.COMPLETED,
                amount=amount,
                description=description or "Заморозка средств",
                balance_before=user.balance,
                balance_after=user.balance
            )
            
            session.add(transaction)
            await session.commit()
            
            logger.info(
                "🧊 Balance frozen",
                telegram_id=telegram_id,
                amount=float(amount),
                frozen_total=float(user.frozen_balance)
            )
            
            return True
    
    async def unfreeze_balance(
        self,
        telegram_id: int,
        amount: Decimal,
        description: str = ""
    ) -> bool:
        """Разморозка средств"""
        async with get_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            # Проверяем наличие замороженных средств
            if user.frozen_balance < amount:
                logger.warning(
                    "❌ Insufficient frozen balance for unfreeze",
                    telegram_id=telegram_id,
                    frozen=float(user.frozen_balance),
                    amount=float(amount)
                )
                return False
            
            # Размораживаем средства
            user.frozen_balance -= amount
            
            # Создаем транзакцию
            transaction = Transaction(
                user_id=telegram_id,
                type=TransactionType.BALANCE_UNFREEZE,
                status=TransactionStatus.COMPLETED,
                amount=amount,
                description=description or "Разморозка средств",
                balance_before=user.balance,
                balance_after=user.balance
            )
            
            session.add(transaction)
            await session.commit()
            
            logger.info(
                "🔓 Balance unfrozen",
                telegram_id=telegram_id,
                amount=float(amount),
                frozen_total=float(user.frozen_balance)
            )
            
            return True
    
    async def update_last_activity(self, telegram_id: int) -> None:
        """Обновление времени последней активности"""
        async with get_session() as session:
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(last_activity=datetime.utcnow())
            )
            await session.commit()
    
    async def get_user_referrals(self, telegram_id: int, limit: int = 50) -> list[User]:
        """Получить список рефералов пользователя"""
        async with get_session() as session:
            result = await session.execute(
                select(User)
                .where(User.referrer_id == telegram_id)
                .order_by(User.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
    
    async def get_user_stats(self, telegram_id: int) -> dict:
        """Получить детальную статистику пользователя"""
        async with get_session() as session:
            user = await self.get_user(telegram_id)
            if not user:
                return {}
            
            # Считаем статистику транзакций
            transactions_stats = await session.execute(
                select(
                    func.count(Transaction.id).label('total_transactions'),
                    func.sum(Transaction.amount).filter(Transaction.amount > 0).label('total_income'),
                    func.sum(Transaction.amount).filter(Transaction.amount < 0).label('total_spending')
                )
                .where(Transaction.user_id == telegram_id)
            )
            
            stats = transactions_stats.first()
            
            return {
                'user': user,
                'total_transactions': stats.total_transactions or 0,
                'total_income': float(stats.total_income or 0),
                'total_spending': float(abs(stats.total_spending or 0)),
                'referrals_count': user.total_referrals,
                'premium_referrals_count': user.premium_referrals,
                'account_age_days': (datetime.utcnow() - user.created_at).days,
                'level_config': user.get_level_config()
            }
    
    def _calculate_user_level(self, balance: Decimal, is_premium: bool = False) -> UserLevel:
        """Расчет уровня пользователя на основе баланса"""
        if is_premium:
            return UserLevel.PREMIUM
        
        if balance >= settings.LEVEL_THRESHOLDS["premium"]:
            return UserLevel.PREMIUM
        elif balance >= settings.LEVEL_THRESHOLDS["gold"]:
            return UserLevel.GOLD
        elif balance >= settings.LEVEL_THRESHOLDS["silver"]:
            return UserLevel.SILVER
        else:
            return UserLevel.BRONZE
    
    async def ban_user(
        self,
        telegram_id: int,
        reason: str,
        banned_by: int
    ) -> bool:
        """Заблокировать пользователя"""
        async with get_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            user.is_banned = True
            user.ban_reason = reason
            user.is_active = False
            
            await session.commit()
            
            logger.warning(
                "🚫 User banned",
                telegram_id=telegram_id,
                reason=reason,
                banned_by=banned_by
            )
            
            return True
    
    async def unban_user(self, telegram_id: int, unbanned_by: int) -> bool:
        """Разблокировать пользователя"""
        async with get_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            user.is_banned = False
            user.ban_reason = None
            user.is_active = True
            
            await session.commit()
            
            logger.info(
                "✅ User unbanned",
                telegram_id=telegram_id,
                unbanned_by=unbanned_by
            )
            
            return True