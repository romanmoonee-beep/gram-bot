"""Валидаторы для проверки пользовательских данных"""

import re
from decimal import Decimal, InvalidOperation
from typing import Tuple, Optional
from urllib.parse import urlparse

from app.config.settings import settings

class ValidationError(Exception):
    """Исключение для ошибок валидации"""
    pass

class TelegramValidator:
    """Валидатор для Telegram данных"""
    
    @staticmethod
    def validate_username(username: str) -> Tuple[bool, str]:
        """Валидация Telegram username"""
        if not username:
            return False, "Username не может быть пустым"
        
        # Убираем @ если есть
        username = username.lstrip('@')
        
        # Проверка формата
        if not re.match(r'^[a-zA-Z0-9_]{5,32}$', username):
            return False, "Username должен содержать 5-32 символа (буквы, цифры, _)"
        
        # Не должен начинаться с цифры
        if username[0].isdigit():
            return False, "Username не может начинаться с цифры"
        
        return True, ""
    
    @staticmethod
    def validate_channel_url(url: str) -> Tuple[bool, str]:
        """Валидация ссылки на канал"""
        if not url:
            return False, "Ссылка не может быть пустой"
        
        # Паттерны для валидных ссылок
        patterns = [
            r'^@[a-zA-Z0-9_]{5,32}$',  # @username
            r'^https://t\.me/[a-zA-Z0-9_]{5,32}/?$',  # https://t.me/username
            r'^https://t\.me/joinchat/[a-zA-Z0-9_-]+/?$',  # Приватные группы
            r'^https://t\.me/\+[a-zA-Z0-9_-]+/?$'  # Новый формат приватных ссылок
        ]
        
        if any(re.match(pattern, url) for pattern in patterns):
            return True, ""
        
        return False, "Некорректная ссылка на канал/группу"
    
    @staticmethod
    def validate_post_url(url: str) -> Tuple[bool, str]:
        """Валидация ссылки на пост"""
        if not url:
            return False, "Ссылка не может быть пустой"
        
        # Паттерн для ссылки на пост
        pattern = r'^https://t\.me/[a-zA-Z0-9_]{5,32}/\d+/?$'
        
        if re.match(pattern, url):
            return True, ""
        
        return False, "Некорректная ссылка на пост"
    
    @staticmethod
    def validate_bot_url(url: str) -> Tuple[bool, str]:
        """Валидация ссылки на бота"""
        if not url:
            return False, "Ссылка не может быть пустой"
        
        # Паттерны для ботов
        patterns = [
            r'^@[a-zA-Z0-9_]{5,32}[Bb]ot$',  # @username с bot в конце
            r'^https://t\.me/[a-zA-Z0-9_]{5,32}[Bb]ot/?$'  # https://t.me/bot
        ]
        
        if any(re.match(pattern, url) for pattern in patterns):
            return True, ""
        
        return False, "Некорректная ссылка на бота"

class TaskValidator:
    """Валидатор для заданий"""
    
    @staticmethod
    def validate_title(title: str) -> Tuple[bool, str]:
        """Валидация названия задания"""
        if not title or not title.strip():
            return False, "Название не может быть пустым"
        
        title = title.strip()
        
        if len(title) < 5:
            return False, "Название слишком короткое (минимум 5 символов)"
        
        if len(title) > 100:
            return False, "Название слишком длинное (максимум 100 символов)"
        
        # Проверка на запрещенные слова
        forbidden_words = [
            'спам', 'развод', 'мошенник', 'fake', 'scam',
            'обман', 'кидалово', 'лохотрон', 'вирус'
        ]
        
        title_lower = title.lower()
        for word in forbidden_words:
            if word in title_lower:
                return False, f"Название содержит запрещенное слово: {word}"
        
        return True, ""
    
    @staticmethod
    def validate_description(description: str) -> Tuple[bool, str]:
        """Валидация описания задания"""
        if not description or not description.strip():
            return False, "Описание не может быть пустым"
        
        description = description.strip()
        
        if len(description) < 10:
            return False, "Описание слишком короткое (минимум 10 символов)"
        
        if len(description) > 1000:
            return False, "Описание слишком длинное (максимум 1000 символов)"
        
        return True, ""
    
    @staticmethod
    def validate_reward(reward: str, user_level: str) -> Tuple[bool, str, Optional[Decimal]]:
        """Валидация награды за задание"""
        try:
            reward_decimal = Decimal(reward.strip())
        except (InvalidOperation, ValueError):
            return False, "Введите корректное число", None
        
        if reward_decimal <= 0:
            return False, "Награда должна быть больше 0", None
        
        min_reward = settings.MIN_TASK_REWARD
        if reward_decimal < min_reward:
            return False, f"Минимальная награда: {min_reward} GRAM", None
        
        max_reward = settings.MAX_TASK_REWARDS.get(user_level, Decimal("500"))
        if reward_decimal > max_reward:
            return False, f"Максимальная награда для вашего уровня: {max_reward} GRAM", None
        
        return True, "", reward_decimal
    
    @staticmethod
    def validate_executions(executions: str) -> Tuple[bool, str, Optional[int]]:
        """Валидация количества выполнений"""
        try:
            executions_int = int(executions.strip())
        except ValueError:
            return False, "Введите корректное число", None
        
        if executions_int < 1:
            return False, "Количество выполнений должно быть больше 0", None
        
        if executions_int > 10000:
            return False, "Максимальное количество выполнений: 10,000", None
        
        return True, "", executions_int

class FinanceValidator:
    """Валидатор для финансовых операций"""
    
    @staticmethod
    def validate_amount(amount: str, min_amount: Decimal = None, max_amount: Decimal = None) -> Tuple[bool, str, Optional[Decimal]]:
        """Валидация денежной суммы"""
        try:
            amount_decimal = Decimal(amount.strip())
        except (InvalidOperation, ValueError):
            return False, "Введите корректную сумму", None
        
        if amount_decimal <= 0:
            return False, "Сумма должна быть больше 0", None
        
        if min_amount and amount_decimal < min_amount:
            return False, f"Минимальная сумма: {min_amount} GRAM", None
        
        if max_amount and amount_decimal > max_amount:
            return False, f"Максимальная сумма: {max_amount} GRAM", None
        
        return True, "", amount_decimal
    
    @staticmethod
    def validate_check_amount(amount: str) -> Tuple[bool, str, Optional[Decimal]]:
        """Валидация суммы чека"""
        return FinanceValidator.validate_amount(
            amount, 
            settings.MIN_CHECK_AMOUNT,
            settings.MAX_CHECK_AMOUNT
        )
