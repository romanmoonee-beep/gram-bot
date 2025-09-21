from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from app.database.models.task import Task, TaskType
from app.database.models.user import User
from app.bot.keyboards.main_menu import MainMenuCallback

class EarnCallback(CallbackData, prefix="earn"):
    """Callback данные для заработка"""
    action: str
    task_type: str = "all"
    task_id: int = 0
    page: int = 1

def get_earn_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню заработка"""
    builder = InlineKeyboardBuilder()
    
    # Типы заданий
    builder.row(
        InlineKeyboardButton(
            text="📺 Подписка на каналы",
            callback_data=EarnCallback(action="list", task_type="channel_subscription").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="👥 Вступить в группы",
            callback_data=EarnCallback(action="list", task_type="group_join").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="👀 Просмотр постов",
            callback_data=EarnCallback(action="list", task_type="post_view").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="👍 Поставить реакции",
            callback_data=EarnCallback(action="list", task_type="post_reaction").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🤖 Перейти в ботов",
            callback_data=EarnCallback(action="list", task_type="bot_interaction").pack()
        )
    )
    
    # Все задания
    builder.row(
        InlineKeyboardButton(
            text="🎯 Все задания",
            callback_data=EarnCallback(action="list", task_type="all").pack()
        )
    )
    
    # Назад в меню
    builder.row(
        InlineKeyboardButton(
            text="🏠 В главное меню",
            callback_data=MainMenuCallback(action="main_menu").pack()
        )
    )
    
    return builder.as_markup()

def get_task_list_keyboard(
    tasks: list[Task], 
    task_type: str = "all", 
    page: int = 1,
    has_next: bool = False
) -> InlineKeyboardMarkup:
    """Клавиатура списка заданий"""
    builder = InlineKeyboardBuilder()
    
    # Задания (по 5 в ряд максимум)
    for task in tasks:
        # Формируем текст кнопки
        reward_text = f"{task.reward_amount:,.0f} GRAM"
        remaining = task.remaining_executions
        
        button_text = f"💰 {reward_text} | {remaining} шт."
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=EarnCallback(action="view", task_id=task.id).pack()
            )
        )
    
    # Навигация
    nav_buttons = []
    
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=EarnCallback(action="list", task_type=task_type, page=page-1).pack()
            )
        )
    
    if has_next:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Вперед",
                callback_data=EarnCallback(action="list", task_type=task_type, page=page+1).pack()
            )
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Кнопки управления
    builder.row(
        InlineKeyboardButton(
            text="🔄 Обновить",
            callback_data=EarnCallback(action="list", task_type=task_type, page=page).pack()
        ),
        InlineKeyboardButton(
            text="⬅️ К типам заданий",
            callback_data=EarnCallback(action="menu").pack()
        )
    )
    
    return builder.as_markup()

def get_task_view_keyboard(task: Task, user: User) -> InlineKeyboardMarkup:
    """Клавиатура просмотра задания"""
    builder = InlineKeyboardBuilder()
    
    # Кнопка выполнения
    if task.is_active and task.can_be_executed_by_user(user.level):
        if task.type in [TaskType.BOT_INTERACTION]:
            button_text = "🤖 Перейти к боту"
        elif task.type == TaskType.CHANNEL_SUBSCRIPTION:
            button_text = "📺 Подписаться"
        elif task.type == TaskType.GROUP_JOIN:
            button_text = "👥 Вступить в группу"
        elif task.type == TaskType.POST_VIEW:
            button_text = "👀 Посмотреть пост"
        elif task.type == TaskType.POST_REACTION:
            button_text = "👍 Поставить реакцию"
        else:
            button_text = "✅ Выполнить"
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=EarnCallback(action="execute", task_id=task.id).pack()
            )
        )
    
    # Информация о задании
    builder.row(
        InlineKeyboardButton(
            text="ℹ️ Подробности",
            callback_data=EarnCallback(action="info", task_id=task.id).pack()
        )
    )
    
    # Навигация
    builder.row(
        InlineKeyboardButton(
            text="⬅️ К списку заданий",
            callback_data=EarnCallback(action="list", task_type=task.type).pack()
        )
    )
    
    return builder.as_markup()

def get_task_execution_keyboard(task: Task) -> InlineKeyboardMarkup:
    """Клавиатура выполнения задания"""
    builder = InlineKeyboardBuilder()
    
    # Кнопка проверки (для автоматических заданий)
    if task.auto_check and not task.manual_review_required:
        builder.row(
            InlineKeyboardButton(
                text="✅ Проверить выполнение",
                callback_data=EarnCallback(action="check", task_id=task.id).pack()
            )
        )
    
    # Отмена
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=EarnCallback(action="view", task_id=task.id).pack()
        )
    )
    
    return builder.as_markup()