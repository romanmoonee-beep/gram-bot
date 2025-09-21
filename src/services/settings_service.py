from __future__ import annotations

from decimal import Decimal
from typing import Optional, Dict, Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_session
from app.database.models.user_settings import UserSettings
from app.database.models.user import User

logger = structlog.get_logger(__name__)

class SettingsService:
    """Сервис для работы с настройками пользователей"""
    
    async def get_user_settings(self, user_id: int) -> UserSettings:
        """Получить настройки пользователя (создать если нет)"""
        async with get_session() as session:
            result = await session.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            settings = result.scalar_one_or_none()
            
            if not settings:
                # Создаем настройки по умолчанию
                settings = UserSettings(user_id=user_id)
                session.add(settings)
                await session.commit()
                await session.refresh(settings)
                
                logger.info("✨ Created default settings", user_id=user_id)
            
            return settings
    
    async def update_notification_setting(
        self,
        user_id: int,
        setting_name: str,
        enabled: bool
    ) -> bool:
        """Обновить настройку уведомлений"""
        async with get_session() as session:
            settings = await self.get_user_settings(user_id)
            
            if setting_name == "tasks":
                settings.task_notifications = enabled
            elif setting_name == "payments":
                settings.payment_notifications = enabled
            elif setting_name == "referrals":
                settings.referral_notifications = enabled
            elif setting_name == "admin":
                settings.admin_notifications = enabled
            else:
                logger.warning("Unknown notification setting", setting=setting_name)
                return False
            
            # Обновляем в сессии
            await session.merge(settings)
            await session.commit()
            
            logger.info(
                "🔔 Notification setting updated",
                user_id=user_id,
                setting=setting_name,
                enabled=enabled
            )
            
            return True
    
    async def update_privacy_setting(
        self,
        user_id: int,
        setting_name: str,
        enabled: bool
    ) -> bool:
        """Обновить настройку приватности"""
        async with get_session() as session:
            settings = await self.get_user_settings(user_id)
            
            if setting_name == "hide_profile":
                settings.hide_profile = enabled
            elif setting_name == "hide_stats":
                settings.hide_stats = enabled
            elif setting_name == "hide_from_leaderboard":
                settings.hide_from_leaderboard = enabled
            elif setting_name == "allow_referral_mentions":
                settings.allow_referral_mentions = enabled
            else:
                logger.warning("Unknown privacy setting", setting=setting_name)
                return False
            
            await session.merge(settings)
            await session.commit()
            
            logger.info(
                "🔒 Privacy setting updated",
                user_id=user_id,
                setting=setting_name,
                enabled=enabled
            )
            
            return True
    
    async def set_language(self, user_id: int, language: str) -> bool:
        """Установить язык пользователя"""
        if language not in ["ru", "en"]:
            logger.warning("Unsupported language", language=language)
            return False
        
        async with get_session() as session:
            settings = await self.get_user_settings(user_id)
            settings.language = language
            
            await session.merge(settings)
            await session.commit()
            
            logger.info("🌐 Language updated", user_id=user_id, language=language)
            return True
    
    async def set_timezone(self, user_id: int, timezone: str) -> bool:
        """Установить часовой пояс"""
        async with get_session() as session:
            settings = await self.get_user_settings(user_id)
            settings.timezone = timezone
            
            await session.merge(settings)
            await session.commit()
            
            logger.info("⏰ Timezone updated", user_id=user_id, timezone=timezone)
            return True
    
    async def setup_auto_withdraw(
        self,
        user_id: int,
        enabled: bool,
        threshold: Decimal = None,
        address: str = None,
        method: str = None
    ) -> bool:
        """Настроить автовывод"""
        async with get_session() as session:
            settings = await self.get_user_settings(user_id)
            
            settings.auto_withdraw_enabled = enabled
            
            if threshold is not None:
                if threshold < Decimal("100"):  # Минимум 100 GRAM
                    logger.warning("Auto-withdraw threshold too low", threshold=float(threshold))
                    return False
                settings.auto_withdraw_threshold = threshold
            
            if address:
                settings.auto_withdraw_address = address
            
            if method:
                if method not in ["card", "crypto", "paypal", "qiwi"]:
                    logger.warning("Unsupported withdraw method", method=method)
                    return False
                settings.auto_withdraw_method = method
            
            await session.merge(settings)
            await session.commit()
            
            logger.info(
                "💸 Auto-withdraw settings updated",
                user_id=user_id,
                enabled=enabled,
                threshold=float(threshold) if threshold else None,
                method=method
            )
            
            return True
    
    async def enable_two_factor(self, user_id: int, enabled: bool) -> bool:
        """Включить/выключить двухфакторную аутентификацию"""
        async with get_session() as session:
            settings = await self.get_user_settings(user_id)
            settings.two_factor_enabled = enabled
            
            await session.merge(settings)
            await session.commit()
            
            logger.info("🔐 Two-factor auth updated", user_id=user_id, enabled=enabled)
            return True
    
    async def toggle_api_access(self, user_id: int, enabled: bool) -> bool:
        """Включить/выключить API доступ"""
        async with get_session() as session:
            settings = await self.get_user_settings(user_id)
            settings.api_access_enabled = enabled
            
            await session.merge(settings)
            await session.commit()
            
            logger.info("🔌 API access updated", user_id=user_id, enabled=enabled)
            return True
    
    async def get_users_with_notifications_enabled(
        self,
        notification_type: str
    ) -> list[int]:
        """Получить список пользователей с включенными уведомлениями"""
        async with get_session() as session:
            if notification_type == "tasks":
                column = UserSettings.task_notifications
            elif notification_type == "payments":
                column = UserSettings.payment_notifications
            elif notification_type == "referrals":
                column = UserSettings.referral_notifications
            elif notification_type == "admin":
                column = UserSettings.admin_notifications
            else:
                return []
            
            result = await session.execute(
                select(UserSettings.user_id)
                .where(column == True)
            )
            
            return [row[0] for row in result.fetchall()]
    
    async def get_user_language(self, user_id: int) -> str:
        """Получить язык пользователя"""
        settings = await self.get_user_settings(user_id)
        return settings.language
    
    async def should_hide_user_profile(self, user_id: int) -> bool:
        """Проверить, скрыт ли профиль пользователя"""
        settings = await self.get_user_settings(user_id)
        return settings.hide_profile
    
    async def should_hide_user_stats(self, user_id: int) -> bool:
        """Проверить, скрыта ли статистика пользователя"""
        settings = await self.get_user_settings(user_id)
        return settings.hide_stats
    
    async def should_show_in_leaderboard(self, user_id: int) -> bool:
        """Проверить, показывать ли в рейтинге"""
        settings = await self.get_user_settings(user_id)
        return not settings.hide_from_leaderboard
    
    async def get_auto_withdraw_users(self, min_balance: Decimal) -> list[dict]:
        """Получить пользователей для автовывода"""
        async with get_session() as session:
            result = await session.execute(
                select(UserSettings, User)
                .join(User, UserSettings.user_id == User.telegram_id)
                .where(
                    UserSettings.auto_withdraw_enabled == True,
                    UserSettings.auto_withdraw_threshold <= min_balance,
                    User.balance >= UserSettings.auto_withdraw_threshold
                )
            )
            
            users = []
            for settings, user in result:
                users.append({
                    'user_id': user.telegram_id,
                    'balance': user.balance,
                    'threshold': settings.auto_withdraw_threshold,
                    'address': settings.auto_withdraw_address,
                    'method': settings.auto_withdraw_method
                })
            
            return users
    
    async def export_user_settings(self, user_id: int) -> dict:
        """Экспортировать настройки пользователя"""
        settings = await self.get_user_settings(user_id)
        return settings.to_dict()
    
    async def import_user_settings(self, user_id: int, settings_data: dict) -> bool:
        """Импортировать настройки пользователя"""
        try:
            async with get_session() as session:
                settings = await self.get_user_settings(user_id)
                
                # Уведомления
                if 'notifications' in settings_data:
                    notif = settings_data['notifications']
                    settings.task_notifications = notif.get('tasks', True)
                    settings.payment_notifications = notif.get('payments', True)
                    settings.referral_notifications = notif.get('referrals', True)
                    settings.admin_notifications = notif.get('admin', True)
                
                # Приватность
                if 'privacy' in settings_data:
                    priv = settings_data['privacy']
                    settings.hide_profile = priv.get('hide_profile', False)
                    settings.hide_stats = priv.get('hide_stats', False)
                    settings.hide_from_leaderboard = priv.get('hide_from_leaderboard', False)
                    settings.allow_referral_mentions = priv.get('allow_referral_mentions', True)
                
                # Локализация
                if 'localization' in settings_data:
                    local = settings_data['localization']
                    settings.language = local.get('language', 'ru')
                    settings.timezone = local.get('timezone', 'UTC')
                
                await session.merge(settings)
                await session.commit()
                
                logger.info("📥 Settings imported", user_id=user_id)
                return True
                
        except Exception as e:
            logger.error("💥 Settings import failed", user_id=user_id, error=str(e))
            return False
