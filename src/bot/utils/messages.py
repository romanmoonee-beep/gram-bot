from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from app.database.models.user import User
from app.database.models.task import Task, TaskType
from app.database.models.task_execution import TaskExecution
from app.config.settings import settings

# ==============================================================================
# ОСНОВНЫЕ СООБЩЕНИЯ
# ==============================================================================

WELCOME_MESSAGE = """🌟 <b>Добро пожаловать в PR GRAM Bot!</b>

Зарабатывайте GRAM за простые действия:
• 📺 Подписки на каналы
• 👥 Вступление в группы  
• 👀 Просмотры постов
• 👍 Реакции и переходы

💰 Тратьте GRAM на продвижение своих проектов

🎁 Приглашайте друзей и получайте бонусы!"""

HELP_MESSAGE = """❓ <b>ПОМОЩЬ</b>

<b>Как зарабатывать GRAM:</b>
1️⃣ Нажмите "💰 Заработать"
2️⃣ Выберите задание
3️⃣ Выполните условия
4️⃣ Получите награду!

<b>Как рекламировать:</b>
1️⃣ Нажмите "📢 Рекламировать" 
2️⃣ Создайте задание
3️⃣ Настройте параметры
4️⃣ Получайте результат!

<b>Telegram Stars:</b>
Пополняйте баланс через встроенную систему платежей Telegram

<b>Поддержка:</b> @prgram_support
<b>Канал новостей:</b> @prgram_news"""

# ==============================================================================
# СООБЩЕНИЯ ОБ ОШИБКАХ
# ==============================================================================

ERROR_MESSAGES = {
    "insufficient_balance": "❌ Недостаточно средств на балансе",
    "task_not_found": "❌ Задание не найдено",
    "task_already_completed": "❌ Вы уже выполнили это задание",
    "task_expired": "❌ Срок выполнения задания истек",
    "task_not_active": "❌ Задание неактивно",
    "invalid_url": "❌ Некорректная ссылка",
    "rate_limit": "⏰ Слишком быстро! Подождите немного",
    "maintenance": "🔧 Технические работы. Попробуйте позже",
    "access_denied": "🚫 Доступ запрещен",
    "user_banned": "❌ Ваш аккаунт заблокирован",
    "level_insufficient": "❌ Ваш уровень недостаточен для этого действия",
    "daily_limit_exceeded": "❌ Превышен дневной лимит",
    "invalid_data": "❌ Некорректные данные",
    "operation_failed": "❌ Операция не удалась"
}

# ==============================================================================
# СООБЩЕНИЯ ОБ УСПЕХЕ
# ==============================================================================

SUCCESS_MESSAGES = {
    "task_completed": "✅ Задание выполнено! +{reward} GRAM",
    "task_created": "✅ Задание создано успешно!",
    "payment_success": "✅ Платеж успешно обработан!",
    "referral_bonus": "🎉 Новый реферал! +{bonus} GRAM",
    "balance_updated": "💰 Баланс обновлен",
    "settings_saved": "⚙️ Настройки сохранены",
    "operation_success": "✅ Операция выполнена успешно"
}

# ==============================================================================
# ФУНКЦИИ ГЕНЕРАЦИИ СООБЩЕНИЙ
# ==============================================================================

def get_welcome_text(user: User) -> str:
    """Генерация приветственного сообщения"""
    level_config = user.get_level_config()
    
    return f"""{WELCOME_MESSAGE}

💎 <b>Ваш статус:</b> {level_config['name']}
💰 <b>Баланс:</b> {user.balance:,.0f} GRAM

Начните с команды /earn или воспользуйтесь меню ниже! 👇"""

def get_main_menu_text(user: User) -> str:
    """Текст главного меню"""
    level_config = user.get_level_config()
    
    return f"""🏠 <b>ГЛАВНОЕ МЕНЮ</b>

Баланс: <b>{user.balance:,.0f} GRAM</b> 💰
Уровень: <b>{level_config['name']}</b> {level_config['emoji']}

Выберите действие:"""

def get_profile_text(user: User) -> str:
    """Текст профиля пользователя"""
    level_config = user.get_level_config()
    
    # Рассчитываем прогресс до следующего уровня
    current_threshold = level_config.get('min_balance', Decimal('0'))
    
    # Определяем следующий уровень
    next_level_info = ""
    if user.level == "bronze":
        next_threshold = settings.LEVEL_THRESHOLDS["silver"]
        next_level_info = f"До Silver: {next_threshold - user.balance:,.0f} GRAM"
    elif user.level == "silver":
        next_threshold = settings.LEVEL_THRESHOLDS["gold"]
        next_level_info = f"До Gold: {next_threshold - user.balance:,.0f} GRAM"
    elif user.level == "gold":
        next_threshold = settings.LEVEL_THRESHOLDS["premium"]
        next_level_info = f"До Premium: {next_threshold - user.balance:,.0f} GRAM"
    else:
        next_level_info = "Максимальный уровень!"
    
    registration_date = user.created_at.strftime('%d.%m.%Y')
    account_age = (datetime.utcnow() - user.created_at).days
    
    return f"""👤 <b>МОЙ КАБИНЕТ</b>

🆔 ID: <code>{user.telegram_id}</code>
👨‍💼 @{user.username or 'не указан'}
📊 Уровень: <b>{level_config['name']}</b>

💰 <b>БАЛАНС:</b>
├ Доступно: <b>{user.available_balance:,.0f} GRAM</b>
├ Заморожено: {user.frozen_balance:,.0f} GRAM
└ {next_level_info}

📈 <b>СТАТИСТИКА:</b>
├ Выполнено заданий: {user.tasks_completed}
├ Создано заданий: {user.tasks_created}  
├ Рефералов: {user.total_referrals} ({user.premium_referrals} Premium)
└ Заработано всего: {user.total_earned:,.0f} GRAM

📅 <b>АККАУНТ:</b>
├ Регистрация: {registration_date}
├ Возраст: {account_age} дн.
└ Последняя активность: {user.last_activity.strftime('%d.%m %H:%M') if user.last_activity else 'давно'}"""

def get_balance_details_text(user: User) -> str:
    """Подробная информация о балансе"""
    level_config = user.get_level_config()
    
    return f"""💰 <b>ПОДРОБНО О БАЛАНСЕ</b>

💳 <b>Текущий баланс:</b>
├ Общий: {user.balance:,.0f} GRAM
├ Доступно: <b>{user.available_balance:,.0f} GRAM</b>
└ Заморожено: {user.frozen_balance:,.0f} GRAM

📊 <b>ДВИЖЕНИЯ СРЕДСТВ:</b>
├ Всего заработано: {user.total_earned:,.0f} GRAM
├ Всего потрачено: {user.total_spent:,.0f} GRAM
├ Пополнений: {user.total_deposited:,.0f} GRAM
└ От рефералов: {user.referral_earnings:,.0f} GRAM

⚙️ <b>НАСТРОЙКИ УРОВНЯ:</b>
├ Комиссия с заданий: {level_config['commission_rate']*100:.0f}%
├ Множитель наград: x{level_config['task_multiplier']}
├ Реферальный бонус: {level_config['referral_bonus']:,.0f} GRAM
└ Дневной лимит заданий: {level_config['max_daily_tasks'] if level_config['max_daily_tasks'] != -1 else '∞'}

💡 <i>Повышайте уровень для лучших условий!</i>"""

def get_task_text(task: Task, user: User | None = None) -> str:
    """Текст задания"""
    # Иконки типов заданий
    type_icons = {
        TaskType.CHANNEL_SUBSCRIPTION: "📺",
        TaskType.GROUP_JOIN: "👥",
        TaskType.POST_VIEW: "👀",
        TaskType.POST_REACTION: "👍",
        TaskType.BOT_INTERACTION: "🤖",
        TaskType.CUSTOM: "⚙️"
    }
    
    # Названия типов
    type_names = {
        TaskType.CHANNEL_SUBSCRIPTION: "Подписка на канал",
        TaskType.GROUP_JOIN: "Вступление в группу",
        TaskType.POST_VIEW: "Просмотр поста",
        TaskType.POST_REACTION: "Реакция на пост",
        TaskType.BOT_INTERACTION: "Взаимодействие с ботом",
        TaskType.CUSTOM: "Пользовательское задание"
    }
    
    icon = type_icons.get(task.type, "🎯")
    type_name = type_names.get(task.type, "Неизвестный тип")
    
    # Рассчитываем награду с учетом множителя пользователя
    final_reward = task.reward_amount
    if user:
        user_config = user.get_level_config()
        final_reward = task.reward_amount * user_config['task_multiplier']
    
    # Информация о времени
    time_info = ""
    if task.expires_at:
        remaining = task.expires_at - datetime.utcnow()
        if remaining.total_seconds() > 0:
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            time_info = f"⏱️ Осталось: {hours}ч {minutes}м"
        else:
            time_info = "⏰ Задание истекло"
    
    # Требования
    requirements = []
    if task.min_user_level:
        level_names = {
            "bronze": "🥉 Bronze",
            "silver": "🥈 Silver", 
            "gold": "🥇 Gold",
            "premium": "💎 Premium"
        }
        req_level = level_names.get(task.min_user_level, task.min_user_level)
        requirements.append(f"Минимальный уровень: {req_level}")
    
    requirements_text = ""
    if requirements:
        requirements_text = "\n\n📋 <b>ТРЕБОВАНИЯ:</b>\n" + "\n".join(f"• {req}" for req in requirements)
    
    return f"""{icon} <b>{task.title}</b>

📝 <b>Тип:</b> {type_name}
💰 <b>Награда:</b> {final_reward:,.0f} GRAM
👥 <b>Выполнено:</b> {task.completed_executions}/{task.target_executions}
{time_info}

📄 <b>ОПИСАНИЕ:</b>
{task.description}

🔗 <b>Ссылка:</b> {task.target_url}{requirements_text}"""

def get_task_list_text(tasks: list[Task], task_type: str = "all", page: int = 1) -> str:
    """Текст списка заданий"""
    # Названия типов для заголовка
    type_titles = {
        "all": "🎯 ВСЕ ЗАДАНИЯ",
        "channel_subscription": "📺 ПОДПИСКА НА КАНАЛЫ",
        "group_join": "👥 ВСТУПЛЕНИЕ В ГРУППЫ",
        "post_view": "👀 ПРОСМОТР ПОСТОВ",
        "post_reaction": "👍 РЕАКЦИИ НА ПОСТЫ",
        "bot_interaction": "🤖 ПЕРЕХОД В БОТОВ"
    }
    
    title = type_titles.get(task_type, "🎯 ЗАДАНИЯ")
    
    if not tasks:
        return f"""{title}

❌ <b>Заданий не найдено</b>

Попробуйте:
• Выбрать другой тип заданий
• Обновить список
• Проверить позже"""
    
    total_reward = sum(task.reward_amount for task in tasks)
    
    return f"""{title}

📊 Найдено: <b>{len(tasks)} заданий</b>
💰 Общая награда: <b>{total_reward:,.0f} GRAM</b>
📄 Страница: {page}

Выберите задание для выполнения:"""

def get_task_execution_text(task: Task, user: User) -> str:
    """Текст выполнения задания"""
    user_config = user.get_level_config()
    final_reward = task.reward_amount * user_config['task_multiplier']
    
    instructions = {
        TaskType.CHANNEL_SUBSCRIPTION: """💡 <b>ИНСТРУКЦИЯ:</b>
1. Нажмите кнопку "📺 Подписаться"
2. Подпишитесь на канал
3. Вернитесь и нажмите "✅ Проверить"

⚠️ <i>Не отписывайтесь сразу после проверки!</i>""",
        
        TaskType.GROUP_JOIN: """💡 <b>ИНСТРУКЦИЯ:</b>
1. Нажмите кнопку "👥 Вступить в группу"
2. Вступите в группу
3. Вернитесь и нажмите "✅ Проверить"

⚠️ <i>Не покидайте группу сразу после проверки!</i>""",
        
        TaskType.BOT_INTERACTION: """💡 <b>ИНСТРУКЦИЯ:</b>
1. Нажмите кнопку "🤖 Перейти к боту"
2. Выполните условия задания
3. Сделайте скриншот результата
4. Загрузите скриншот для проверки

⏰ <i>Проверка может занять до 24 часов</i>""",
        
        TaskType.POST_VIEW: """💡 <b>ИНСТРУКЦИЯ:</b>
1. Нажмите кнопку "👀 Посмотреть пост"
2. Прочитайте/просмотрите пост
3. Вернитесь и нажмите "✅ Проверить"

⚠️ <i>Убедитесь, что пост полностью загрузился!</i>""",
        
        TaskType.POST_REACTION: """💡 <b>ИНСТРУКЦИЯ:</b>
1. Нажмите кнопку "👍 Поставить реакцию"
2. Поставьте нужную реакцию на пост
3. Вернитесь и нажмите "✅ Проверить"

⚠️ <i>Не убирайте реакцию после проверки!</i>"""
    }
    
    instruction = instructions.get(task.type, "Следуйте инструкциям задания")
    
    return f"""🎯 <b>ВЫПОЛНЕНИЕ ЗАДАНИЯ</b>

📋 <b>Задание:</b> {task.title}
💰 <b>Ваша награда:</b> {final_reward:,.0f} GRAM
⏱️ <b>Время на выполнение:</b> {settings.TASK_EXECUTION_TIMEOUT // 60} минут

{instruction}"""

def get_referral_text(user: User) -> str:
    """Текст реферальной системы"""
    level_config = user.get_level_config()
    referral_link = f"https://t.me/{settings.BOT_USERNAME}?start={user.telegram_id}"
    
    # Рассчитываем доходность рефералов
    avg_referral_income = 0
    if user.total_referrals > 0:
        avg_referral_income = user.referral_earnings / user.total_referrals
    
    return f"""🔗 <b>РЕФЕРАЛЬНАЯ СИСТЕМА</b>

💰 <b>ВАШИ ДОХОДЫ:</b>
├ За регистрации: {level_config['referral_bonus']:,.0f} GRAM за реферала
├ За активность: 5% от заработка рефералов
├ За пополнения: 10% от депозитов рефералов
└ Всего заработано: {user.referral_earnings:,.0f} GRAM

👥 <b>СТАТИСТИКА:</b>
├ Всего рефералов: {user.total_referrals}
├ Premium рефералов: {user.premium_referrals}
├ Средний доход с реферала: {avg_referral_income:,.0f} GRAM
└ Конверсия в Premium: {(user.premium_referrals/user.total_referrals*100 if user.total_referrals > 0 else 0):.1f}%

🔗 <b>ВАША ССЫЛКА:</b>
<code>{referral_link}</code>

💡 <i>Приглашайте друзей и зарабатывайте на их активности!</i>"""

def get_deposit_text(package_name: str) -> str:
    """Текст пополнения через Stars"""
    package = settings.get_stars_package(package_name)
    if not package:
        return "❌ Пакет не найден"
    
    base_gram, bonus_gram = settings.calculate_gram_from_stars(package["stars"], package_name)
    total_gram = base_gram + bonus_gram
    
    bonus_text = ""
    if bonus_gram > 0:
        bonus_text = f"\n🎁 <b>Бонус:</b> +{bonus_gram:,.0f} GRAM"
    
    if package.get("bonus_percent", 0) > 0:
        bonus_text += f"\n💰 <b>Экономия:</b> {package['bonus_percent']}%"
    
    return f"""💳 <b>ПОПОЛНЕНИЕ БАЛАНСА</b>

📦 <b>Пакет:</b> {package['title']}
⭐ <b>Стоимость:</b> {package['stars']} Telegram Stars
💰 <b>Получите:</b> {total_gram:,.0f} GRAM{bonus_text}

📱 <b>Как оплатить:</b>
1. Нажмите кнопку "Оплатить"
2. Подтвердите покупку Stars в Telegram
3. GRAM поступят автоматически

⚡ <i>Зачисление происходит мгновенно!</i>"""

def get_my_tasks_text(tasks: list[Task], page: int = 1) -> str:
    """Текст моих заданий"""
    if not tasks:
        return """🎯 <b>МОИ ЗАДАНИЯ</b>

📭 <b>У вас пока нет заданий</b>

Создайте свое первое задание:
• Выберите тип задания
• Настройте параметры
• Получайте результат!"""
    
    # Статистика по статусам
    active_count = sum(1 for task in tasks if task.status.value == "active")
    completed_count = sum(1 for task in tasks if task.status.value == "completed")
    total_spent = sum(task.spent_budget for task in tasks)
    total_executions = sum(task.completed_executions for task in tasks)
    
    return f"""🎯 <b>МОИ ЗАДАНИЯ</b>

📊 <b>СТАТИСТИКА:</b>
├ Активных: {active_count}
├ Завершенных: {completed_count}
├ Потрачено: {total_spent:,.0f} GRAM
└ Выполнений: {total_executions}

📄 Страница: {page}

Выберите задание для управления:"""

def get_task_analytics_text(analytics: dict) -> str:
    """Текст аналитики задания"""
    task = analytics['task']
    
    return f"""📊 <b>АНАЛИТИКА ЗАДАНИЯ</b>

🎯 <b>Задание:</b> {task.title}
📅 <b>Создано:</b> {task.created_at.strftime('%d.%m.%Y %H:%M')}

📈 <b>ПРОГРЕСС:</b>
├ Выполнено: {task.completed_executions}/{task.target_executions}
├ Прогресс: {task.completion_percentage:.1f}%
├ Конверсия: {analytics['completion_rate']:.1f}%
└ Осталось: {task.remaining_executions}

💰 <b>БЮДЖЕТ:</b>
├ Общий: {analytics['budget_utilization']['total']:,.0f} GRAM
├ Потрачено: {analytics['budget_utilization']['spent']:,.0f} GRAM
├ Остается: {analytics['budget_utilization']['remaining']:,.0f} GRAM
└ Использовано: {analytics['budget_utilization']['utilization_percent']:.1f}%

⏱️ <b>ВРЕМЯ ВЫПОЛНЕНИЯ:</b>
├ Среднее: {analytics['timing']['average_seconds']:.0f} сек
├ Быстрейшее: {analytics['timing']['fastest_seconds']:.0f} сек
└ Самое долгое: {analytics['timing']['slowest_seconds']:.0f} сек

📋 <b>СТАТИСТИКА ВЫПОЛНЕНИЙ:</b>"""

def format_task_execution_stats(executions_by_status: dict) -> str:
    """Форматирование статистики выполнений"""
    status_names = {
        "pending": "⏳ Ожидают",
        "completed": "✅ Завершены",
        "rejected": "❌ Отклонены",
        "expired": "⏰ Истекшие"
    }
    
    lines = []
    for status, count in executions_by_status.items():
        name = status_names.get(status, status)
        lines.append(f"├ {name}: {count}")
    
    return "\n".join(lines)

def get_admin_stats_text(stats: dict) -> str:
    """Текст админской статистики"""
    return f"""📊 <b>СТАТИСТИКА СИСТЕМЫ</b>

🎯 <b>ЗАДАНИЯ:</b>
├ Активных: {stats['tasks']['by_status'].get('active', {}).get('count', 0)}
├ Завершенных: {stats['tasks']['by_status'].get('completed', {}).get('count', 0)}
├ Приостановленных: {stats['tasks']['by_status'].get('paused', {}).get('count', 0)}
└ Общий бюджет: {stats['tasks']['total_budget']:,.0f} GRAM

💼 <b>ВЫПОЛНЕНИЯ:</b>
├ Ожидают проверки: {stats['executions']['by_status'].get('pending', {}).get('count', 0)}
├ Завершенных: {stats['executions']['by_status'].get('completed', {}).get('count', 0)}
├ Отклоненных: {stats['executions']['by_status'].get('rejected', {}).get('count', 0)}
└ Общие награды: {stats['executions']['total_rewards']:,.0f} GRAM

📈 <b>ЗА 24 ЧАСА:</b>
├ Новых заданий: {stats['recent_24h']['new_tasks']}
└ Новых выполнений: {stats['recent_24h']['new_executions']}

⚡ <i>Данные обновляются в реальном времени</i>"""

def get_error_message(error_key: str, **kwargs) -> str:
    """Получить сообщение об ошибке"""
    message = ERROR_MESSAGES.get(error_key, "❌ Неизвестная ошибка")
    try:
        return message.format(**kwargs)
    except (KeyError, ValueError):
        return message

def get_success_message(success_key: str, **kwargs) -> str:
    """Получить сообщение об успехе"""
    message = SUCCESS_MESSAGES.get(success_key, "✅ Операция выполнена")
    try:
        return message.format(**kwargs)
    except (KeyError, ValueError):
        return message

# ==============================================================================
# УТИЛИТЫ ФОРМАТИРОВАНИЯ
# ==============================================================================

def format_datetime(dt: datetime) -> str:
    """Форматирование даты и времени"""
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} дн. назад"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} ч. назад"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} мин. назад"
    else:
        return "только что"

def format_duration(seconds: int) -> str:
    """Форматирование длительности"""
    if seconds < 60:
        return f"{seconds} сек"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} мин"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}ч {minutes}м"

def format_gram_amount(amount: Decimal | float) -> str:
    """Форматирование суммы GRAM"""
    if isinstance(amount, Decimal):
        amount = float(amount)
    
    if amount >= 1000000:
        return f"{amount/1000000:.1f}M GRAM"
    elif amount >= 1000:
        return f"{amount/1000:.1f}K GRAM"
    else:
        return f"{amount:,.0f} GRAM"

def format_percentage(value: float, total: float) -> str:
    """Форматирование процента"""
    if total == 0:
        return "0%"
    
    percentage = (value / total) * 100
    return f"{percentage:.1f}%"

def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезание длинного текста"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

def escape_html(text: str) -> str:
    """Экранирование HTML символов"""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;"))

def format_user_mention(user: User) -> str:
    """Форматирование упоминания пользователя"""
    display_name = user.first_name or user.username or str(user.telegram_id)
    return f'<a href="tg://user?id={user.telegram_id}">{escape_html(display_name)}</a>'

def get_level_emoji(level: str) -> str:
    """Получить эмодзи уровня"""
    emojis = {
        "bronze": "🥉",
        "silver": "🥈", 
        "gold": "🥇",
        "premium": "💎"
    }
    return emojis.get(level, "❓")

def get_task_type_emoji(task_type: TaskType) -> str:
    """Получить эмодзи типа задания"""
    emojis = {
        TaskType.CHANNEL_SUBSCRIPTION: "📺",
        TaskType.GROUP_JOIN: "👥",
        TaskType.POST_VIEW: "👀",
        TaskType.POST_REACTION: "👍",
        TaskType.BOT_INTERACTION: "🤖",
        TaskType.CUSTOM: "⚙️"
    }
    return emojis.get(task_type, "🎯")

def get_status_emoji(status: str) -> str:
    """Получить эмодзи статуса"""
    emojis = {
        "active": "🟢",
        "paused": "⏸️",
        "completed": "✅",
        "cancelled": "❌",
        "expired": "⏰",
        "pending": "⏳",
        "rejected": "❌"
    }
    return emojis.get(status, "❓")

# ==============================================================================
# ВАЛИДАЦИЯ И ПРОВЕРКИ
# ==============================================================================

def validate_url(url: str) -> bool:
    """Проверка корректности URL"""
    import re
    
    # Паттерны для Telegram ссылок
    patterns = [
        r'^https://t\.me/[a-zA-Z0-9_]+/?,  # Канал/группа
        r'^https://t\.me/[a-zA-Z0-9_]+/\d+/?,  # Пост
        r'^@[a-zA-Z0-9_]+,  # Username
        r'^https://t\.me/\+[a-zA-Z0-9_-]+/?  # Приватная ссылка
    ]
    
    return any(re.match(pattern, url) for pattern in patterns)

def validate_task_title(title: str) -> tuple[bool, str]:
    """Валидация названия задания"""
    if not title or not title.strip():
        return False, "Название не может быть пустым"
    
    if len(title) > 255:
        return False, "Название слишком длинное (максимум 255 символов)"
    
    if len(title) < 5:
        return False, "Название слишком короткое (минимум 5 символов)"
    
    # Проверка на запрещенные слова
    forbidden_words = ["спам", "развод", "мошенник", "fake"]
    if any(word in title.lower() for word in forbidden_words):
        return False, "Название содержит запрещенные слова"
    
    return True, ""

def validate_reward_amount(amount: Decimal, user_level: str) -> tuple[bool, str]:
    """Валидация суммы награды"""
    if amount < settings.MIN_TASK_REWARD:
        return False, f"Минимальная награда: {settings.MIN_TASK_REWARD} GRAM"
    
    max_reward = settings.MAX_TASK_REWARDS.get(user_level, Decimal("500"))
    if amount > max_reward:
        return False, f"Максимальная награда для вашего уровня: {max_reward} GRAM"
    
    return True, ""

def can_user_create_task(user: User) -> tuple[bool, str]:
    """Проверка возможности создания задания пользователем"""
    if not user.is_active:
        return False, "Аккаунт неактивен"
    
    if user.is_banned:
        return False, f"Аккаунт заблокирован: {user.ban_reason}"
    
    # Проверка дневного лимита
    config = user.get_level_config()
    daily_limit = config['max_daily_tasks']
    
    if daily_limit != -1:  # Не безлимит
        today = datetime.utcnow().date()
        if user.last_task_date and user.last_task_date.date() == today:
            if user.daily_tasks_created >= daily_limit:
                return False, f"Превышен дневной лимит: {daily_limit} заданий"
    
    return True, ""