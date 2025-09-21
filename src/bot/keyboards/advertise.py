from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from app.database.models.task import Task, TaskType, TaskStatus
from app.database.models.user import User
from app.bot.keyboards.main_menu import MainMenuCallback

class AdvertiseCallback(CallbackData, prefix="adv"):
    """Callback данные для рекламы"""
    action: str
    task_type: str = "none"
    task_id: int = 0
    page: int = 1

def get_advertise_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню рекламы"""
    builder = InlineKeyboardBuilder()
    
    # Создание заданий
    builder.row(
        InlineKeyboardButton(
            text="📺 Подписка на канал",
            callback_data=AdvertiseCallback(action="create", task_type="channel_subscription").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="👥 Вступление в группу",
            callback_data=AdvertiseCallback(action="create", task_type="group_join").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="👀 Просмотр поста",
            callback_data=AdvertiseCallback(action="create", task_type="post_view").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="👍 Реакция на пост",
            callback_data=AdvertiseCallback(action="create", task_type="post_reaction").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🤖 Переход в бота",
            callback_data=AdvertiseCallback(action="create", task_type="bot_interaction").pack()
        )
    )
    
    # Управление заданиями
    builder.row(
        InlineKeyboardButton(
            text="🎯 Мои задания",
            callback_data=AdvertiseCallback(action="my_tasks").pack()
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

def get_my_tasks_keyboard(
    tasks: list[Task], 
    page: int = 1,
    has_next: bool = False
) -> InlineKeyboardMarkup:
    """Клавиатура моих заданий"""
    builder = InlineKeyboardBuilder()
    
    # Задания
    for task in tasks:
        # Иконка статуса
        status_icons = {
            TaskStatus.ACTIVE: "🟢",
            TaskStatus.PAUSED: "⏸️",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.CANCELLED: "❌",
            TaskStatus.EXPIRED: "⏰"
        }
        
        status_icon = status_icons.get(task.status, "❓")
        progress = f"{task.completed_executions}/{task.target_executions}"
        
        button_text = f"{status_icon} {task.title[:20]}... | {progress}"
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=AdvertiseCallback(action="manage", task_id=task.id).pack()
            )
        )
    
    # Навигация
    nav_buttons = []
    
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=AdvertiseCallback(action="my_tasks", page=page-1).pack()
            )
        )
    
    if has_next:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Вперед", 
                callback_data=AdvertiseCallback(action="my_tasks", page=page+1).pack()
            )
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Кнопки управления
    builder.row(
        InlineKeyboardButton(
            text="➕ Создать новое",
            callback_data=AdvertiseCallback(action="menu").pack()
        ),
        InlineKeyboardButton(
            text="🔄 Обновить",
            callback_data=AdvertiseCallback(action="my_tasks", page=page).pack()
        )
    )
    
    return builder.as_markup()

def get_task_management_keyboard(task: Task) -> InlineKeyboardMarkup:
    """Клавиатура управления заданием"""
    builder = InlineKeyboardBuilder()
    
    # Основные действия в зависимости от статуса
    if task.status == TaskStatus.ACTIVE:
        builder.row(
            InlineKeyboardButton(
                text="⏸️ Приостановить",
                callback_data=AdvertiseCallback(action="pause", task_id=task.id).pack()
            )
        )
    elif task.status == TaskStatus.PAUSED:
        builder.row(
            InlineKeyboardButton(
                text="▶️ Возобновить",
                callback_data=AdvertiseCallback(action="resume", task_id=task.id).pack()
            )
        )
    
    # Аналитика
    builder.row(
        InlineKeyboardButton(
            text="📊 Аналитика",
            callback_data=AdvertiseCallback(action="analytics", task_id=task.id).pack()
        )
    )
    
    # Отмена (только для незавершенных заданий)
    if task.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
        builder.row(
            InlineKeyboardButton(
                text="❌ Отменить задание",
                callback_data=AdvertiseCallback(action="cancel", task_id=task.id).pack()
            )
        )
    
    # Назад к списку
    builder.row(
        InlineKeyboardButton(
            text="⬅️ К моим заданиям",
            callback_data=AdvertiseCallback(action="my_tasks").pack()
        )
    )
    
    return builder.as_markup()

def get_task_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа задания"""
    builder = InlineKeyboardBuilder()
    
    task_types = [
        ("📺 Подписка на канал", "channel_subscription"),
        ("👥 Вступление в группу", "group_join"), 
        ("👀 Просмотр поста", "post_view"),
        ("👍 Реакция на пост", "post_reaction"),
        ("🤖 Переход в бота", "bot_interaction")
    ]
    
    for text, task_type in task_types:
        builder.row(
            InlineKeyboardButton(
                text=text,
                callback_data=AdvertiseCallback(action="create", task_type=task_type).pack()
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=AdvertiseCallback(action="menu").pack()
        )
    )
    
    return builder.as_markup()