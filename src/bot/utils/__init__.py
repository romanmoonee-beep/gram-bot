"""Утилиты для Telegram бота"""

from .messages import (
    # Основные сообщения
    WELCOME_MESSAGE,
    HELP_MESSAGE,
    ERROR_MESSAGES,
    SUCCESS_MESSAGES,
    
    # Генераторы текста
    get_welcome_text,
    get_main_menu_text,
    get_profile_text,
    get_balance_details_text,
    get_task_text,
    get_task_list_text,
    get_task_execution_text,
    get_referral_text,
    get_deposit_text,
    get_my_tasks_text,
    get_task_analytics_text,
    get_admin_stats_text,
    
    # Утилиты форматирования
    format_datetime,
    format_duration,
    format_gram_amount,
    format_percentage,
    truncate_text,
    escape_html,
    format_user_mention,
    
    # Эмодзи
    get_level_emoji,
    get_task_type_emoji,
    get_status_emoji,
    
    # Валидация
    validate_url,
    validate_task_title,
    validate_reward_amount,
    can_user_create_task,
    
    # Сообщения
    get_error_message,
    get_success_message
)

__all__ = [
    # Константы сообщений
    "WELCOME_MESSAGE",
    "HELP_MESSAGE", 
    "ERROR_MESSAGES",
    "SUCCESS_MESSAGES",
    
    # Генераторы
    "get_welcome_text",
    "get_main_menu_text",
    "get_profile_text",
    "get_balance_details_text",
    "get_task_text",
    "get_task_list_text",
    "get_task_execution_text",
    "get_referral_text",
    "get_deposit_text",
    "get_my_tasks_text",
    "get_task_analytics_text",
    "get_admin_stats_text",
    
    # Форматирование
    "format_datetime",
    "format_duration",
    "format_gram_amount",
    "format_percentage",
    "truncate_text",
    "escape_html",
    "format_user_mention",
    
    # Эмодзи
    "get_level_emoji",
    "get_task_type_emoji",
    "get_status_emoji",
    
    # Валидация
    "validate_url",
    "validate_task_title",
    "validate_reward_amount",
    "can_user_create_task",
    
    # Сообщения
    "get_error_message",
    "get_success_message"
]