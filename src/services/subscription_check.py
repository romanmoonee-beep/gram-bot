from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_session
from app.database.models.check import Check, CheckActivation, CheckType, CheckStatus
from app.database.models.user import User
from app.database.models.transaction import TransactionType
from app.services.user_service import UserService
from app.services.transaction_service import TransactionService
from app.config.settings import settings

logger = structlog.get_logger(__name__)

class CheckService:
    """Сервис для работы с чеками"""
    
    def __init__(self):
        self.user_service = UserService()
        self.transaction_service = TransactionService()
    
    def _generate_check_code(self) -> str:
        """Генерация уникального кода чека"""
        # Генерируем код из 8 символов (буквы + цифры)
        alphabet = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(8))
    
    async def create_check(
        self,
        creator_id: int,
        check_type: CheckType,
        total_amount: Decimal,
        max_activations: int = 1,
        title: str | None = None,
        description: str | None = None,
        password: str | None = None,
        required_subscription_channel: str | None = None,
        min_user_level: str | None = None,
        expires_in_hours: int | None = None,
        max_per_user: int = 1
    ) -> Check | None:
        """Создать новый чек"""
        
        async with get_session() as session:
            # Получаем создателя
            creator = await self.user_service.get_user(creator_id)
            if not creator:
                logger.error("❌ Creator not found", creator_id=creator_id)
                return None
            
            # Проверяем баланс
            if creator.available_balance < total_amount:
                logger.warning(
                    "❌ Insufficient balance for check creation",
                    creator_id=creator_id,
                    required=float(total_amount),
                    available=float(creator.available_balance)
                )
                return None
            
            # Рассчитываем сумму на активацию
            amount_per_activation = total_amount / max_activations
            
            # Генерируем уникальный код
            attempts = 0
            while attempts < 10:
                check_code = self._generate_check_code()
                
                # Проверяем уникальность
                existing = await session.execute(
                    select(Check).where(Check.check_code == check_code)
                )
                if not existing.scalar_one_or_none():
                    break
                    
                attempts += 1
            else:
                logger.error("❌ Failed to generate unique check code")
                return None
            
            # Замораживаем средства у создателя
            await self.user_service.freeze_balance(
                creator_id,
                total_amount,
                f"Создание чека #{check_code}"
            )
            
            # Создаем чек
            expires_at = None
            if expires_in_hours:
                expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
            
            check = Check(
                creator_id=creator_id,
                type=check_type,
                total_amount=total_amount,
                amount_per_activation=amount_per_activation,
                remaining_amount=total_amount,
                max_activations=max_activations,
                max_per_user=max_per_user,
                check_code=check_code,
                title=title,
                description=description,
                password=password,
                required_subscription_channel=required_subscription_channel,
                min_user_level=min_user_level,
                expires_at=expires_at
            )
            
            session.add(check)
            await session.commit()
            await session.refresh(check)
            
            logger.info(
                "💳 Check created",
                check_id=check.id,
                check_code=check_code,
                creator_id=creator_id,
                amount=float(total_amount),
                activations=max_activations
            )
            
            return check
    
    async def get_check_by_code(self, check_code: str) -> Check | None:
        """Получить чек по коду"""
        async with get_session() as session:
            result = await session.execute(
                select(Check).where(Check.check_code == check_code.upper())
            )
            return result.scalar_one_or_none()
    
    async def activate_check(
        self,
        check_code: str,
        user_id: int,
        password: str | None = None
    ) -> tuple[bool, str, Decimal]:
        """
        Активировать чек
        Возвращает: (успех, сообщение, сумма)
        """
        
        async with get_session() as session:
            # Получаем чек
            check = await self.get_check_by_code(check_code)
            if not check:
                return False, "❌ Чек не найден", Decimal("0")
            
            # Проверяем активность чека
            if not check.is_active:
                if check.status == CheckStatus.EXPIRED:
                    return False, "⏰ Срок действия чека истек", Decimal("0")
                elif check.status == CheckStatus.COMPLETED:
                    return False, "✅ Чек уже полностью активирован", Decimal("0")
                elif check.status == CheckStatus.CANCELLED:
                    return False, "❌ Чек отменен", Decimal("0")
                else:
                    return False, "❌ Чек неактивен", Decimal("0")
            
            # Проверяем, не создатель ли пытается активировать
            if check.creator_id == user_id:
                return False, "❌ Нельзя активировать собственный чек", Decimal("0")
            
            # Проверяем пароль
            if check.password and check.password != password:
                return False, "🔒 Неверный пароль", Decimal("0")
            
            # Проверяем условия пользователя
            user = await self.user_service.get_user(user_id)
            if not user:
                return False, "❌ Пользователь не найден", Decimal("0")
            
            # Проверяем минимальный уровень
            if check.min_user_level:
                level_hierarchy = ["bronze", "silver", "gold", "premium"]
                if user.level not in level_hierarchy:
                    return False, "❌ Неизвестный уровень пользователя", Decimal("0")
                
                required_index = level_hierarchy.index(check.min_user_level)
                user_index = level_hierarchy.index(user.level)
                
                if user_index < required_index:
                    level_names = {
                        "bronze": "🥉 Bronze",
                        "silver": "🥈 Silver",
                        "gold": "🥇 Gold", 
                        "premium": "💎 Premium"
                    }
                    required_level = level_names.get(check.min_user_level, check.min_user_level)
                    return False, f"❌ Требуется уровень {required_level}", Decimal("0")
            
            # Проверяем лимит активаций на пользователя
            user_activations = await session.execute(
                select(func.count(CheckActivation.id))
                .where(
                    and_(
                        CheckActivation.check_id == check.id,
                        CheckActivation.user_id == user_id
                    )
                )
            )
            
            user_activation_count = user_activations.scalar() or 0
            if user_activation_count >= check.max_per_user:
                return False, "❌ Вы уже активировали этот чек", Decimal("0")
            
            # Проверяем обязательную подписку
            if check.required_subscription_channel:
                # Здесь должна быть проверка подписки через Telegram API
                # Пока что пропускаем эту проверку
                pass
            
            # Активируем чек
            activation = CheckActivation(
                check_id=check.id,
                user_id=user_id,
                amount_received=check.amount_per_activation
            )
            
            session.add(activation)
            
            # Обновляем чек
            check.current_activations += 1
            check.remaining_amount -= check.amount_per_activation
            
            # Проверяем завершение чека
            if check.current_activations >= check.max_activations or check.remaining_amount <= 0:
                check.status = CheckStatus.COMPLETED
                
                # Возвращаем оставшиеся средства создателю если есть
                if check.remaining_amount > 0:
                    await self.user_service.unfreeze_balance(
                        check.creator_id,
                        check.remaining_amount,
                        f"Возврат средств с чека #{check.check_code}"
                    )
            
            # Начисляем средства получателю
            await self.user_service.update_balance(
                user_id,
                check.amount_per_activation,
                TransactionType.CHECK_RECEIVED,
                f"Получение чека #{check.check_code}",
                str(check.id),
                "check"
            )
            
            # Списываем с создателя (размораживаем)
            await self.user_service.unfreeze_balance(
                check.creator_id,
                check.amount_per_activation,
                f"Активация чека #{check.check_code} пользователем @{user.username or user.telegram_id}"
            )
            
            await session.commit()
            
            logger.info(
                "💳 Check activated",
                check_id=check.id,
                check_code=check.check_code,
                user_id=user_id,
                amount=float(check.amount_per_activation)
            )
            
            return True, "✅ Чек успешно активирован!", check.amount_per_activation
    
    async def get_user_checks(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> list[Check]:
        """Получить чеки пользователя"""
        async with get_session() as session:
            result = await session.execute(
                select(Check)
                .where(Check.creator_id == user_id)
                .order_by(desc(Check.created_at))
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())
    
    async def get_user_activations(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> list[CheckActivation]:
        """Получить активации чеков пользователя"""
        async with get_session() as session:
            result = await session.execute(
                select(CheckActivation)
                .where(CheckActivation.user_id == user_id)
                .order_by(desc(CheckActivation.activated_at))
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())
    
    async def cancel_check(self, check_id: int, creator_id: int) -> bool:
        """Отменить чек"""
        async with get_session() as session:
            result = await session.execute(
                select(Check).where(
                    and_(Check.id == check_id, Check.creator_id == creator_id)
                )
            )
            check = result.scalar_one_or_none()
            
            if not check or check.status != CheckStatus.ACTIVE:
                return False
            
            check.status = CheckStatus.CANCELLED
            
            # Возвращаем средства создателю
            if check.remaining_amount > 0:
                await self.user_service.unfreeze_balance(
                    creator_id,
                    check.remaining_amount,
                    f"Отмена чека #{check.check_code}"
                )
            
            await session.commit()
            
            logger.info(
                "❌ Check cancelled",
                check_id=check_id,
                check_code=check.check_code,
                creator_id=creator_id
            )
            
            return True
    
    async def get_check_analytics(self, check_id: int) -> dict | None:
        """Получить аналитику чека"""
        async with get_session() as session:
            check = await session.execute(
                select(Check).where(Check.id == check_id)
            )
            check = check.scalar_one_or_none()
            
            if not check:
                return None
            
            # Статистика активаций
            activations = await session.execute(
                select(CheckActivation)
                .where(CheckActivation.check_id == check_id)
                .order_by(CheckActivation.activated_at)
            )
            activations_list = list(activations.scalars().all())
            
            return {
                'check': check,
                'total_activations': len(activations_list),
                'total_distributed': float(check.total_amount - check.remaining_amount),
                'completion_percentage': (check.current_activations / check.max_activations * 100) if check.max_activations > 0 else 0,
                'activations': activations_list,
                'is_expired': check.expires_at and datetime.utcnow() > check.expires_at if check.expires_at else False
            }
    
    async def cleanup_expired_checks(self) -> int:
        """Очистка истекших чеков"""
        async with get_session() as session:
            # Находим истекшие чеки
            expired_checks = await session.execute(
                select(Check).where(
                    and_(
                        Check.status == CheckStatus.ACTIVE,
                        Check.expires_at <= datetime.utcnow()
                    )
                )
            )
            
            count = 0
            for check in expired_checks.scalars():
                check.status = CheckStatus.EXPIRED
                
                # Возвращаем оставшиеся средства
                if check.remaining_amount > 0:
                    await self.user_service.unfreeze_balance(
                        check.creator_id,
                        check.remaining_amount,
                        f"Истечение срока чека #{check.check_code}"
                    )
                
                count += 1
            
            await session.commit()
            
            if count > 0:
                logger.info("🧹 Expired checks cleaned up", count=count)
            
            return count
