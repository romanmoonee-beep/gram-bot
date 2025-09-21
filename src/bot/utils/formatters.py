"""Форматтеры для отображения данных в удобном виде"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Union, List, Optional

from app.database.models.user import User
from app.database.models.task import Task, TaskType, TaskStatus
from app.database.models.task_execution import TaskExecution, ExecutionStatus

class NumberFormatter:
    """Форматтер для чисел и валют"""
    
    @staticmethod
    def format_gram(amount: Union[Decimal, float, int]) -> str:
        """Форматирование суммы GRAM с красивыми сокращениями"""
        if isinstance(amount, Decimal):
            amount = float(amount)
        
        if amount >= 1_000_000:
            return f"{amount/1_000_000:.1f}M GRAM"
        elif amount >= 1_000:
            return f"{amount/1_000:.1f}K GRAM"
        else:
            return f"{amount:,.0f} GRAM"
    
    @staticmethod
    def format_gram_detailed(amount: Union[Decimal, float, int]) -> str:
        """Детальное форматирование GRAM с разделителями"""
        if isinstance(amount, Decimal):
            amount = float(amount)
        
        return f"{amount:,.0f} GRAM"
    
    @staticmethod
    def format_number(number: Union[int, float]) -> str:
        """Форматирование больших чисел с сокращениями"""
        if number >= 1_000_000:
            return f"{number/1_000_000:.1f}M"
        elif number >= 1_000:
            return f"{number/1_000:.1f}K"
        else:
            return f"{number:,.0f}"
    
    @staticmethod
    def format_percentage(value: float, total: float, decimals: int = 1) -> str:
        """Форматирование процентов"""
        if total == 0:
            return "0%"
        
        percentage = (value / total) * 100
        return f"{percentage:.{decimals}f}%"
    
    @staticmethod
    def format_commission(rate: float) -> str:
        """Форматирование комиссии"""
        return f"{rate * 100:.1f}%"

class TimeFormatter:
    """Форматтер для времени и дат"""
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """Форматирование длительности в читаемый вид"""
        if seconds < 60:
            return f"{seconds} сек"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            if remaining_seconds > 0:
                return f"{minutes}м {remaining_seconds}с"
            return f"{minutes}м"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours}ч {minutes}м"
            return f"{hours}ч"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            if hours > 0:
                return f"{days}д {hours}ч"
            return f"{days}д"
    
    @staticmethod
    def format_relative_time(dt: datetime) -> str:
        """Форматирование относительного времени (назад от текущего)"""
        now = datetime.utcnow()
        diff = now - dt
        
        if diff.days > 0:
            if diff.days == 1:
                return "вчера"
            elif diff.days < 7:
                return f"{diff.days} дн. назад"
            elif diff.days < 30:
                weeks = diff.days // 7
                return f"{weeks} нед. назад"
            elif diff.days < 365:
                months = diff.days // 30
                return f"{months} мес. назад"
            else:
                years = diff.days // 365
                return f"{years} г. назад"
        
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} ч. назад"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} мин. назад"
        else:
            return "только что"
    
    @staticmethod
    def format_time_remaining(end_time: datetime) -> str:
        """Форматирование оставшегося времени до даты"""
        now = datetime.utcnow()
        remaining = end_time - now
        
        if remaining.total_seconds() <= 0:
            return "истекло"
        
        days = remaining.days
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        
        if days > 0:
            if hours > 0:
                return f"{days}д {hours}ч"
            return f"{days}д"
        elif hours > 0:
            if minutes > 0:
                return f"{hours}ч {minutes}м"
            return f"{hours}ч"
        else:
            return f"{minutes}м"
    
    @staticmethod
    def format_datetime(dt: datetime, show_time: bool = True) -> str:
        """Форматирование даты и времени"""
        if show_time:
            return dt.strftime('%d.%m.%Y %H:%M')
        else:
            return dt.strftime('%d.%m.%Y')
    
    @staticmethod
    def format_time_only(dt: datetime) -> str:
        """Форматирование только времени"""
        return dt.strftime('%H:%M')

class TextFormatter:
    """Форматтер для текста и строк"""
    
    @staticmethod
    def truncate(text: str, max_length: int = 50, suffix: str = "...") -> str:
        """Обрезание длинного текста с добавлением суффикса"""
        if not text:
            return ""
        
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def escape_html(text: str) -> str:
        """Экранирование HTML символов для безопасного отображения"""
        if not text:
            return ""
        
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#x27;"))
    
    @staticmethod
    def format_list(items: List[str], max_items: int = 5, separator: str = ", ") -> str:
        """Форматирование списка с ограничением количества элементов"""
        if not items:
            return "пусто"
        
        if len(items) <= max_items:
            return separator.join(items)
        
        visible_items = items[:max_items]
        remaining = len(items) - max_items
        
        return f"{separator.join(visible_items)} и еще {remaining}"
    
    @staticmethod
    def format_username(username: Optional[str], telegram_id: int) -> str:
        """Форматирование имени пользователя"""
        if username:
            return f"@{username}"
        else:
            return f"ID{telegram_id}"
    
    @staticmethod
    def format_multiline_list(items: List[str], prefix: str = "├", last_prefix: str = "└") -> str:
        """Форматирование списка в несколько строк с красивыми префиксами"""
        if not items:
            return ""
        
        formatted_items = []
        for i, item in enumerate(items):
            if i == len(items) - 1:
                formatted_items.append(f"{last_prefix} {item}")
            else:
                formatted_items.append(f"{prefix} {item}")
        
        return "\n".join(formatted_items)

class StatusFormatter:
    """Форматтер для статусов и состояний"""
    
    @staticmethod
    def format_user_level(level: str) -> str:
        """Форматирование уровня пользователя с эмодзи"""
        level_formats = {
            "bronze": "🥉 Bronze",
            "silver": "🥈 Silver", 
            "gold": "🥇 Gold",
            "premium": "💎 Premium"
        }
        return level_formats.get(level, f"❓ {level}")
    
    @staticmethod
    def format_task_type(task_type: TaskType) -> str:
        """Форматирование типа задания"""
        type_formats = {
            TaskType.CHANNEL_SUBSCRIPTION: "📺 Подписка на канал",
            TaskType.GROUP_JOIN: "👥 Вступление в группу",
            TaskType.POST_VIEW: "👀 Просмотр поста",
            TaskType.POST_REACTION: "👍 Реакция на пост",
            TaskType.BOT_INTERACTION: "🤖 Взаимодействие с ботом",
            TaskType.CUSTOM: "⚙️ Пользовательское"
        }
        return type_formats.get(task_type, "❓ Неизвестно")
    
    @staticmethod
    def format_task_status(status: TaskStatus) -> str:
        """Форматирование статуса задания"""
        status_formats = {
            TaskStatus.DRAFT: "📝 Черновик",
            TaskStatus.ACTIVE: "🟢 Активное",
            TaskStatus.PAUSED: "⏸️ Приостановлено",
            TaskStatus.COMPLETED: "✅ Завершено",
            TaskStatus.CANCELLED: "❌ Отменено",
            TaskStatus.EXPIRED: "⏰ Истекло"
        }
        return status_formats.get(status, "❓ Неизвестно")
    
    @staticmethod
    def format_execution_status(status: ExecutionStatus) -> str:
        """Форматирование статуса выполнения"""
        status_formats = {
            ExecutionStatus.PENDING: "⏳ Ожидает проверки",
            ExecutionStatus.IN_PROGRESS: "🔄 В процессе",
            ExecutionStatus.COMPLETED: "✅ Выполнено",
            ExecutionStatus.REJECTED: "❌ Отклонено",
            ExecutionStatus.EXPIRED: "⏰ Истекло",
            ExecutionStatus.CANCELLED: "🚫 Отменено"
        }
        return status_formats.get(status, "❓ Неизвестно")
    
    @staticmethod
    def get_level_emoji(level: str) -> str:
        """Получить только эмодзи уровня"""
        emojis = {
            "bronze": "🥉",
            "silver": "🥈", 
            "gold": "🥇",
            "premium": "💎"
        }
        return emojis.get(level, "❓")
    
    @staticmethod
    def get_status_emoji(status: str) -> str:
        """Получить эмодзи статуса"""
        emojis = {
            "active": "🟢",
            "paused": "⏸️",
            "completed": "✅",
            "cancelled": "❌",
            "expired": "⏰",
            "pending": "⏳",
            "rejected": "❌",
            "draft": "📝"
        }
        return emojis.get(status.lower(), "❓")

class ProgressFormatter:
    """Форматтер для прогресса и статистики"""
    
    @staticmethod
    def format_progress_bar(current: int, total: int, length: int = 10) -> str:
        """Создание текстового прогресс-бара"""
        if total == 0:
            return "░" * length
        
        filled = int((current / total) * length)
        return "█" * filled + "░" * (length - filled)
    
    @staticmethod
    def format_completion_stats(completed: int, total: int) -> str:
        """Форматирование статистики завершения"""
        percentage = (completed / total * 100) if total > 0 else 0
        return f"{completed}/{total} ({percentage:.1f}%)"
    
    @staticmethod
    def format_task_progress(task: Task) -> str:
        """Форматирование прогресса задания"""
        progress_bar = ProgressFormatter.format_progress_bar(
            task.completed_executions, 
            task.target_executions,
            8
        )
        stats = ProgressFormatter.format_completion_stats(
            task.completed_executions,
            task.target_executions
        )
        return f"{progress_bar} {stats}"

class TableFormatter:
    """Форматтер для табличных данных"""
    
    @staticmethod
    def format_stats_table(stats: dict, title: str = "СТАТИСТИКА") -> str:
        """Форматирование статистики в виде таблицы"""
        lines = [f"📊 <b>{title}</b>", ""]
        
        for key, value in stats.items():
            if isinstance(value, (int, float)):
                if isinstance(value, float) and value != int(value):
                    formatted_value = f"{value:.2f}"
                else:
                    formatted_value = f"{int(value):,}"
            else:
                formatted_value = str(value)
            
            lines.append(f"├ {key}: {formatted_value}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_referral_list(referrals: List[User], page: int = 1) -> str:
        """Форматирование списка рефералов"""
        if not referrals:
            return "📭 Список рефералов пуст"
        
        lines = [f"👥 <b>РЕФЕРАЛЫ</b> (стр. {page}):", ""]
        
        for i, referral in enumerate(referrals, 1):
            level_emoji = StatusFormatter.get_level_emoji(referral.level)
            username = TextFormatter.format_username(referral.username, referral.telegram_id)
            date = TimeFormatter.format_datetime(referral.created_at, show_time=False)
            
            lines.append(f"{i}. {level_emoji} {username}")
            lines.append(f"   ├ Регистрация: {date}")
            lines.append(f"   ├ Заданий: {referral.tasks_completed}")
            lines.append(f"   └ Баланс: {NumberFormatter.format_gram(referral.balance)}")
            lines.append("")
        
        return "\n".join(lines[:-1])  # Убираем последнюю пустую строку