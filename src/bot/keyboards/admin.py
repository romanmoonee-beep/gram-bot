from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

class AdminCallback(CallbackData, prefix="admin"):
    """Callback данные для админки"""
    action: str
    target_id: int = 0
    page: int = 1

def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню админки"""
    builder = InlineKeyboardBuilder()
    
    # Модерация
    builder.row(
        InlineKeyboardButton(
            text="🔍 Модерация заданий",
            callback_data=AdminCallback(action="moderation").pack()
        )
    )
    
    # Управление пользователями
    builder.row(
        InlineKeyboardButton(
            text="👥 Управление пользователями",
            callback_data=AdminCallback(action="users").pack()
        )
    )
    
    # Статистика
    builder.row(
        InlineKeyboardButton(
            text="📊 Статистика системы",
            callback_data=AdminCallback(action="stats").pack()
        ),
        InlineKeyboardButton(
            text="💰 Финансовая статистика",
            callback_data=AdminCallback(action="finance_stats").pack()
        )
    )
    
    # Системные функции
    builder.row(
        InlineKeyboardButton(
            text="⚙️ Системные функции",
            callback_data=AdminCallback(action="system").pack()
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

def get_moderation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура модерации"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="⏳ Ожидают проверки",
            callback_data=AdminCallback(action="pending_tasks").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🔄 Автообработка",
            callback_data=AdminCallback(action="auto_process").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в админку",
            callback_data=AdminCallback(action="menu").pack()
        )
    )
    
    return builder.as_markup()

def get_task_moderation_keyboard(execution_id: int) -> InlineKeyboardMarkup:
    """Клавиатура модерации конкретного задания"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="✅ Принять",
            callback_data=AdminCallback(action="approve", target_id=execution_id).pack()
        ),
        InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=AdminCallback(action="reject", target_id=execution_id).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ К списку",
            callback_data=AdminCallback(action="pending_tasks").pack()
        )
    )
    
    return builder.as_markup()