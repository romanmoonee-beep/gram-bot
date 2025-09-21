from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import structlog

from app.services.telegram_api_service import TelegramAPIService
from app.config.settings import settings

logger = structlog.get_logger(__name__)

class SubscriptionService:
    """Сервис для системы обязательной подписки (ОП)"""
    
    def __init__(self):
        self.telegram_api = TelegramAPIService()
        # Храним настройки чатов в памяти (в реальности - в Redis/БД)
        self.chat_settings: Dict[int, Dict] = {}
    
    def _get_chat_settings(self, chat_id: int) -> Dict[str, Any]:
        """Получить настройки чата"""
        return self.chat_settings.get(chat_id, {
            'required_channels': [],
            'check_duration': None,
            'auto_delete_time': None,
            'referral_check': False,
            'referral_user_id': None,
            'enabled': False
        })
    
    def _save_chat_settings(self, chat_id: int, settings: Dict[str, Any]):
        """Сохранить настройки чата"""
        self.chat_settings[chat_id] = settings
        logger.info("💾 Chat settings saved", chat_id=chat_id, settings=settings)
    
    async def setup_channel_check(
        self,
        chat_id: int,
        channel_username: str,
        duration_hours: Optional[int] = None
    ) -> tuple[bool, str]:
        """
        Настроить проверку подписки на канал
        /setup @channel [1d|5h|30m]
        """
        
        # Проверяем существование канала
        channel_url = f"@{channel_username.lstrip('@')}"
        channel_info = await self.telegram_api.get_chat_info(channel_url)
        
        if not channel_info:
            return False, f"❌ Канал {channel_url} не найден или недоступен"
        
        # Получаем текущие настройки
        settings = self._get_chat_settings(chat_id)
        
        # Добавляем канал к проверке
        channel_config = {
            'username': channel_username.lstrip('@'),
            'url': channel_url,
            'title': channel_info.get('title', channel_username),
            'duration_hours': duration_hours,
            'added_at': datetime.utcnow().isoformat()
        }
        
        # Проверяем лимит (максимум 5 каналов)
        if len(settings['required_channels']) >= 5:
            return False, "❌ Максимум 5 каналов для проверки"
        
        # Проверяем, не добавлен ли уже этот канал
        for existing in settings['required_channels']:
            if existing['username'] == channel_config['username']:
                return False, f"❌ Канал {channel_url} уже добавлен в проверку"
        
        # Добавляем канал
        settings['required_channels'].append(channel_config)
        settings['enabled'] = True
        
        self._save_chat_settings(chat_id, settings)
        
        duration_text = ""
        if duration_hours:
            duration_text = f" на {duration_hours} ч."
        
        return True, f"✅ Добавлена проверка подписки на {channel_url}{duration_text}"
    
    async def remove_channel_check(
        self,
        chat_id: int,
        channel_username: str = None
    ) -> tuple[bool, str]:
        """
        Убрать проверку подписки
        /unsetup @channel - убрать конкретный канал
        /unsetup - убрать все проверки
        """
        
        settings = self._get_chat_settings(chat_id)
        
        if not settings['required_channels']:
            return False, "❌ Проверки подписок не настроены"
        
        if channel_username:
            # Убираем конкретный канал
            username = channel_username.lstrip('@')
            original_count = len(settings['required_channels'])
            
            settings['required_channels'] = [
                ch for ch in settings['required_channels']
                if ch['username'] != username
            ]
            
            if len(settings['required_channels']) == original_count:
                return False, f"❌ Канал @{username} не найден в проверках"
            
            # Если каналов не осталось, отключаем проверку
            if not settings['required_channels']:
                settings['enabled'] = False
            
            self._save_chat_settings(chat_id, settings)
            return True, f"✅ Убрана проверка подписки на @{username}"
        else:
            # Убираем все проверки
            settings['required_channels'] = []
            settings['enabled'] = False
            
            self._save_chat_settings(chat_id, settings)
            return True, "✅ Все проверки подписок отключены"
    
    async def setup_referral_check(
        self,
        chat_id: int,
        referral_user_id: int,
        duration_hours: Optional[int] = None
    ) -> tuple[bool, str]:
        """
        Настроить реферальную ОП
        /setup_bot USER_ID [1d]
        """
        
        settings = self._get_chat_settings(chat_id)
        
        settings['referral_check'] = True
        settings['referral_user_id'] = referral_user_id
        settings['check_duration'] = duration_hours
        settings['enabled'] = True
        
        self._save_chat_settings(chat_id, settings)
        
        duration_text = ""
        if duration_hours:
            duration_text = f" на {duration_hours} ч."
        
        referral_link = f"https://t.me/{settings.BOT_USERNAME}?start={referral_user_id}"
        
        return True, f"""✅ Настроена реферальная ОП{duration_text}

🔗 Реферальная ссылка: {referral_link}

Новые участники должны перейти по этой ссылке перед вступлением в группу."""
    
    async def remove_referral_check(self, chat_id: int) -> tuple[bool, str]:
        """Убрать реферальную ОП"""
        
        settings = self._get_chat_settings(chat_id)
        
        if not settings['referral_check']:
            return False, "❌ Реферальная ОП не настроена"
        
        settings['referral_check'] = False
        settings['referral_user_id'] = None
        
        # Если нет других проверок, отключаем ОП
        if not settings['required_channels']:
            settings['enabled'] = False
        
        self._save_chat_settings(chat_id, settings)
        
        return True, "✅ Реферальная ОП отключена"
    
    async def setup_auto_delete(
        self,
        chat_id: int,
        delete_time_seconds: int
    ) -> tuple[bool, str]:
        """
        Настроить автоудаление сообщений
        /autodelete 30s|2m|5m
        """
        
        if delete_time_seconds < 15 or delete_time_seconds > 300:  # 15 сек - 5 мин
            return False, "❌ Время автоудаления: от 15 секунд до 5 минут"
        
        settings = self._get_chat_settings(chat_id)
        settings['auto_delete_time'] = delete_time_seconds
        
        self._save_chat_settings(chat_id, settings)
        
        return True, f"✅ Автоудаление сообщений через {delete_time_seconds} сек."
    
    async def disable_auto_delete(self, chat_id: int) -> tuple[bool, str]:
        """Отключить автоудаление"""
        
        settings = self._get_chat_settings(chat_id)
        settings['auto_delete_time'] = None
        
        self._save_chat_settings(chat_id, settings)
        
        return True, "✅ Автоудаление отключено"
    
    async def get_status(self, chat_id: int) -> str:
        """Получить статус настроек ОП в чате"""
        
        settings = self._get_chat_settings(chat_id)
        
        if not settings['enabled']:
            return """📋 <b>СТАТУС ПРОВЕРКИ ПОДПИСОК</b>

❌ Проверка подписок отключена

🔧 <b>Команды для настройки:</b>
• <code>/setup @channel</code> - добавить проверку канала
• <code>/setup_bot USER_ID</code> - реферальная ОП
• <code>/autodelete 30s</code> - автоудаление сообщений"""
        
        status_text = "📋 <b>СТАТУС ПРОВЕРКИ ПОДПИСОК</b>\n\n✅ Проверка активна\n"
        
        # Проверка каналов
        if settings['required_channels']:
            status_text += f"\n📺 <b>ОБЯЗАТЕЛЬНЫЕ КАНАЛЫ ({len(settings['required_channels'])}):</b>\n"
            for i, channel in enumerate(settings['required_channels'], 1):
                username = channel['username']
                title = channel.get('title', username)
                duration = channel.get('duration_hours')
                
                duration_text = f" ({duration}ч)" if duration else ""
                status_text += f"{i}. @{username} - {title}{duration_text}\n"
        
        # Реферальная проверка
        if settings['referral_check']:
            user_id = settings['referral_user_id']
            duration = settings.get('check_duration')
            duration_text = f" ({duration}ч)" if duration else ""
            
            status_text += f"\n🔗 <b>РЕФЕРАЛЬНАЯ ОП:</b>\n"
            status_text += f"├ Пользователь: {user_id}\n"
            status_text += f"└ Ссылка: https://t.me/{settings.BOT_USERNAME}?start={user_id}{duration_text}\n"
        
        # Автоудаление
        if settings['auto_delete_time']:
            status_text += f"\n⌛ <b>АВТОУДАЛЕНИЕ:</b> {settings['auto_delete_time']} сек.\n"
        
        status_text += f"\n🔧 <b>Команды:</b>\n"
        status_text += f"• <code>/unsetup</code> - отключить все\n"
        status_text += f"• <code>/unsetup @channel</code> - убрать канал\n"
        status_text += f"• <code>/unsetup_bot</code> - убрать реферальную ОП"
        
        return status_text
    
    async def check_new_member(
        self,
        chat_id: int,
        user_id: int,
        username: str = None
    ) -> tuple[bool, str, List[str]]:
        """
        Проверить нового участника при входе в группу
        Возвращает: (разрешен_вход, сообщение, нарушения)
        """
        
        settings = self._get_chat_settings(chat_id)
        
        if not settings['enabled']:
            return True, "", []
        
        violations = []
        
        # Проверяем подписки на каналы
        for channel in settings['required_channels']:
            channel_url = f"@{channel['username']}"
            
            # Проверяем срок действия проверки
            if channel.get('duration_hours'):
                added_time = datetime.fromisoformat(channel['added_at'])
                expires_time = added_time + timedelta(hours=channel['duration_hours'])
                
                if datetime.utcnow() > expires_time:
                    # Проверка истекла, пропускаем
                    continue
            
            # Проверяем подписку
            is_subscribed = await self.telegram_api.check_user_subscription(
                user_id, channel_url
            )
            
            if not is_subscribed:
                violations.append(f"@{channel['username']}")
        
        # Проверяем реферальную систему
        if settings['referral_check']:
            # Здесь должна быть проверка через базу данных рефералов
            # Пока что пропускаем эту проверку
            pass
        
        # Формируем результат
        if violations:
            violation_list = "\n".join(f"• {v}" for v in violations)
            
            message = f"""❌ <b>НЕОБХОДИМА ПОДПИСКА</b>

Для участия в группе подпишитесь на:
{violation_list}

После подписки попробуйте войти снова."""
            
            return False, message, violations
        
        return True, "✅ Проверка пройдена", []
    
    async def process_chat_member_update(
        self,
        chat_id: int,
        user_id: int,
        old_status: str,
        new_status: str,
        username: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Обработать изменение статуса участника чата
        Вызывается при получении chat_member update
        """
        
        # Новый участник (left/kicked -> member)
        if old_status in ['left', 'kicked'] and new_status == 'member':
            allowed, message, violations = await self.check_new_member(
                chat_id, user_id, username
            )
            
            if not allowed:
                return {
                    'action': 'restrict',
                    'message': message,
                    'violations': violations,
                    'auto_delete': self._get_chat_settings(chat_id).get('auto_delete_time')
                }
        
        return None
    
    def parse_duration(self, duration_str: str) -> Optional[int]:
        """
        Парсинг строки времени в часы
        Примеры: 1d -> 24, 5h -> 5, 30m -> 0.5
        """
        
        if not duration_str:
            return None
        
        duration_str = duration_str.lower().strip()
        
        # Паттерны времени
        if duration_str.endswith('d'):
            try:
                days = int(duration_str[:-1])
                return days * 24
            except ValueError:
                return None
        elif duration_str.endswith('h'):
            try:
                hours = int(duration_str[:-1])
                return hours
            except ValueError:
                return None
        elif duration_str.endswith('m'):
            try:
                minutes = int(duration_str[:-1])
                return max(1, minutes // 60)  # Минимум 1 час
            except ValueError:
                return None
        
        return None
    
    def parse_auto_delete_time(self, time_str: str) -> Optional[int]:
        """
        Парсинг времени автоудаления в секунды
        Примеры: 30s -> 30, 2m -> 120, 5m -> 300
        """
        
        if not time_str:
            return None
        
        time_str = time_str.lower().strip()
        
        if time_str.endswith('s'):
            try:
                seconds = int(time_str[:-1])
                return seconds
            except ValueError:
                return None
        elif time_str.endswith('m'):
            try:
                minutes = int(time_str[:-1])
                return minutes * 60
            except ValueError:
                return None
        
        return None
    
    async def cleanup_expired_checks(self) -> int:
        """Очистка истекших проверок"""
        cleaned_count = 0
        current_time = datetime.utcnow()
        
        for chat_id, settings in list(self.chat_settings.items()):
            if not settings.get('enabled'):
                continue
            
            # Проверяем каналы на истечение срока
            original_channels = settings['required_channels'][:]
            active_channels = []
            
            for channel in original_channels:
                if channel.get('duration_hours'):
                    added_time = datetime.fromisoformat(channel['added_at'])
                    expires_time = added_time + timedelta(hours=channel['duration_hours'])
                    
                    if current_time <= expires_time:
                        active_channels.append(channel)
                    else:
                        cleaned_count += 1
                        logger.info(
                            "🧹 Expired channel check removed",
                            chat_id=chat_id,
                            channel=channel['username']
                        )
                else:
                    active_channels.append(channel)
            
            # Обновляем настройки
            settings['required_channels'] = active_channels
            
            # Отключаем ОП если нет активных проверок
            if not active_channels and not settings.get('referral_check'):
                settings['enabled'] = False
            
            self._save_chat_settings(chat_id, settings)
        
        if cleaned_count > 0:
            logger.info("🧹 Cleanup completed", expired_checks=cleaned_count)
        
        return cleaned_count
    
    async def get_chat_analytics(self, chat_id: int) -> Dict[str, Any]:
        """Получить аналитику ОП для чата"""
        
        settings = self._get_chat_settings(chat_id)
        
        analytics = {
            'enabled': settings['enabled'],
            'channels_count': len(settings.get('required_channels', [])),
            'referral_check': settings.get('referral_check', False),
            'auto_delete_enabled': settings.get('auto_delete_time') is not None,
            'channels': []
        }
        
        # Аналитика по каналам
        for channel in settings.get('required_channels', []):
            channel_stats = await self.telegram_api.get_channel_stats(f"@{channel['username']}")
            
            channel_analytics = {
                'username': channel['username'],
                'title': channel.get('title'),
                'member_count': channel_stats.get('member_count', 0) if channel_stats else 0,
                'duration_hours': channel.get('duration_hours'),
                'added_at': channel.get('added_at'),
                'is_expired': False
            }
            
            # Проверяем истечение
            if channel.get('duration_hours'):
                added_time = datetime.fromisoformat(channel['added_at'])
                expires_time = added_time + timedelta(hours=channel['duration_hours'])
                channel_analytics['is_expired'] = datetime.utcnow() > expires_time
            
            analytics['channels'].append(channel_analytics)
        
        return analytics
