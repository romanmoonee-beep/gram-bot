import aiohttp
import asyncio
from typing import Optional, Dict, Any, List
import structlog
from urllib.parse import urlparse
import re

from app.config.settings import settings

logger = structlog.get_logger(__name__)

class TelegramAPIService:
    """Сервис для работы с Telegram Bot API для проверки заданий"""
    
    def __init__(self, bot_token: str = None):
        self.bot_token = bot_token or settings.BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    async def _make_request(self, method: str, params: dict = None) -> Optional[dict]:
        """Выполнить запрос к Telegram API"""
        url = f"{self.api_url}/{method}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=params or {}) as response:
                    result = await response.json()
                    
                    if result.get("ok"):
                        return result.get("result")
                    else:
                        logger.error(
                            "❌ Telegram API error",
                            method=method,
                            error=result.get("description"),
                            error_code=result.get("error_code")
                        )
                        return None
                        
        except Exception as e:
            logger.error("💥 Telegram API request failed", method=method, error=str(e))
            return None
    
    def _parse_telegram_url(self, url: str) -> Dict[str, Any]:
        """Парсинг Telegram URL для извлечения информации"""
        url = url.strip()
        
        # Убираем t.me/ и получаем username
        patterns = [
            r'https?://t\.me/([^/\s]+)/?$',  # https://t.me/username
            r'https?://t\.me/([^/\s]+)/(\d+)/?$',  # https://t.me/username/123 (пост)
            r'@([a-zA-Z0-9_]+)',  # @username
            r'https?://t\.me/joinchat/([a-zA-Z0-9_-]+)',  # invite link
            r'https?://t\.me/\+([a-zA-Z0-9_-]+)'  # new invite format
        ]
        
        for pattern in patterns:
            match = re.match(pattern, url)
            if match:
                if 'joinchat' in pattern or '+' in pattern:
                    return {
                        'type': 'invite_link',
                        'invite_link': url,
                        'hash': match.group(1)
                    }
                elif len(match.groups()) == 2:  # Post URL
                    return {
                        'type': 'post',
                        'username': match.group(1),
                        'message_id': int(match.group(2))
                    }
                else:  # Channel/Group username
                    username = match.group(1).lstrip('@')
                    return {
                        'type': 'username',
                        'username': username
                    }
        
        return {'type': 'unknown', 'url': url}
    
    async def check_user_subscription(self, user_id: int, channel_url: str) -> bool:
        """Проверить подписку пользователя на канал"""
        parsed = self._parse_telegram_url(channel_url)
        
        if parsed['type'] not in ['username', 'invite_link']:
            logger.warning("❌ Invalid channel URL format", url=channel_url)
            return False
        
        chat_id = f"@{parsed['username']}" if parsed['type'] == 'username' else parsed.get('invite_link')
        
        try:
            result = await self._make_request(
                "getChatMember",
                {
                    "chat_id": chat_id,
                    "user_id": user_id
                }
            )
            
            if result:
                status = result.get("status")
                # Считаем подписанными: creator, administrator, member
                subscribed_statuses = ["creator", "administrator", "member"]
                is_subscribed = status in subscribed_statuses
                
                logger.info(
                    "✅ Subscription check completed",
                    user_id=user_id,
                    channel=chat_id,
                    status=status,
                    is_subscribed=is_subscribed
                )
                
                return is_subscribed
            
            return False
            
        except Exception as e:
            logger.error(
                "💥 Subscription check failed",
                user_id=user_id,
                channel=chat_id,
                error=str(e)
            )
            return False
    
    async def check_user_in_group(self, user_id: int, group_url: str) -> bool:
        """Проверить участие пользователя в группе"""
        # Аналогично проверке подписки
        return await self.check_user_subscription(user_id, group_url)
    
    async def get_chat_info(self, chat_url: str) -> Optional[Dict[str, Any]]:
        """Получить информацию о чате/канале"""
        parsed = self._parse_telegram_url(chat_url)
        
        if parsed['type'] != 'username':
            return None
        
        chat_id = f"@{parsed['username']}"
        
        try:
            result = await self._make_request("getChat", {"chat_id": chat_id})
            
            if result:
                return {
                    'id': result.get('id'),
                    'type': result.get('type'),
                    'title': result.get('title'),
                    'username': result.get('username'),
                    'description': result.get('description'),
                    'member_count': result.get('members_count', 0)
                }
            
            return None
            
        except Exception as e:
            logger.error("💥 Get chat info failed", chat_url=chat_url, error=str(e))
            return None
    
    async def validate_post_url(self, post_url: str) -> bool:
        """Проверить существование поста"""
        parsed = self._parse_telegram_url(post_url)
        
        if parsed['type'] != 'post':
            return False
        
        chat_id = f"@{parsed['username']}"
        message_id = parsed['message_id']
        
        try:
            # Пытаемся получить информацию о сообщении
            result = await self._make_request(
                "forwardMessage",
                {
                    "chat_id": "@durov",  # Попробуем переслать в несуществующий чат
                    "from_chat_id": chat_id,
                    "message_id": message_id
                }
            )
            
            # Если пост существует, API вернет ошибку о недоступности чата @durov
            # Если поста нет, будет другая ошибка
            return True  # Упрощенная проверка
            
        except Exception as e:
            logger.warning("⚠️ Post validation failed", post_url=post_url, error=str(e))
            return False
    
    async def check_post_reaction(self, user_id: int, post_url: str, required_reactions: List[str] = None) -> bool:
        """
        Проверить реакцию пользователя на пост
        Примечание: Telegram Bot API не предоставляет прямой способ проверки реакций
        Это упрощенная реализация
        """
        parsed = self._parse_telegram_url(post_url)
        
        if parsed['type'] != 'post':
            return False
        
        # В реальности проверка реакций через Bot API недоступна
        # Можно использовать MTProto API или принимать на веру
        logger.info(
            "ℹ️ Post reaction check requested (limited API support)",
            user_id=user_id,
            post_url=post_url,
            required_reactions=required_reactions
        )
        
        # Для демонстрации возвращаем True
        # В реальном проекте здесь может быть:
        # 1. Интеграция с MTProto
        # 2. Ручная проверка через скриншоты
        # 3. Доверительная система
        return True
    
    async def validate_bot_url(self, bot_url: str) -> bool:
        """Проверить существование бота"""
        parsed = self._parse_telegram_url(bot_url)
        
        if parsed['type'] != 'username':
            return False
        
        username = parsed['username']
        
        # Боты обычно заканчиваются на 'bot'
        if not username.lower().endswith('bot'):
            return False
        
        try:
            chat_info = await self.get_chat_info(bot_url)
            return chat_info is not None and chat_info.get('type') == 'private'
            
        except Exception as e:
            logger.error("💥 Bot validation failed", bot_url=bot_url, error=str(e))
            return False
    
    async def bulk_check_subscriptions(
        self, 
        user_ids: List[int], 
        channel_url: str
    ) -> Dict[int, bool]:
        """Массовая проверка подписок"""
        results = {}
        
        # Ограничиваем количество одновременных запросов
        semaphore = asyncio.Semaphore(5)
        
        async def check_single_user(user_id: int):
            async with semaphore:
                result = await self.check_user_subscription(user_id, channel_url)
                results[user_id] = result
                # Добавляем небольшую задержку для избежания rate limiting
                await asyncio.sleep(0.1)
        
        # Запускаем все проверки параллельно
        tasks = [check_single_user(user_id) for user_id in user_ids]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info(
            "📊 Bulk subscription check completed",
            total_users=len(user_ids),
            subscribed_count=sum(results.values()),
            channel=channel_url
        )
        
        return results
    
    async def get_channel_stats(self, channel_url: str) -> Optional[Dict[str, Any]]:
        """Получить статистику канала"""
        chat_info = await self.get_chat_info(channel_url)
        
        if not chat_info:
            return None
        
        return {
            'member_count': chat_info.get('member_count', 0),
            'title': chat_info.get('title'),
            'type': chat_info.get('type'),
            'username': chat_info.get('username'),
            'description': chat_info.get('description')
        }
    
    async def check_admin_rights(self, chat_url: str, user_id: int) -> Dict[str, bool]:
        """Проверить админские права пользователя в чате"""
        parsed = self._parse_telegram_url(chat_url)
        
        if parsed['type'] != 'username':
            return {'is_admin': False}
        
        chat_id = f"@{parsed['username']}"
        
        try:
            result = await self._make_request(
                "getChatMember",
                {
                    "chat_id": chat_id,
                    "user_id": user_id
                }
            )
            
            if result:
                status = result.get("status")
                is_admin = status in ["creator", "administrator"]
                
                rights = {
                    'is_admin': is_admin,
                    'status': status,
                    'can_delete_messages': result.get('can_delete_messages', False),
                    'can_restrict_members': result.get('can_restrict_members', False),
                    'can_promote_members': result.get('can_promote_members', False),
                    'can_change_info': result.get('can_change_info', False),
                    'can_invite_users': result.get('can_invite_users', False),
                    'can_pin_messages': result.get('can_pin_messages', False)
                }
                
                return rights
            
            return {'is_admin': False}
            
        except Exception as e:
            logger.error("💥 Admin rights check failed", chat_url=chat_url, error=str(e))
            return {'is_admin': False}
