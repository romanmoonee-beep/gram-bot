from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from app.database.models.user import User

class MainMenuCallback(CallbackData, prefix="menu"):
    """Callback данные для главного меню"""
    action: str
    data: str = "none"

def get_main_menu_keyboard(user: User | None = None) -> InlineKeyboardMarkup:
    """Клавиатура главного меню"""
    builder = InlineKeyboardBuilder()
    
    # Первый ряд - личный кабинет
    builder.row(
        InlineKeyboardButton(
            text="👤 Мой кабинет",
            callback_data=MainMenuCallback(action="profile").pack()
        )
    )
    
    # Второй ряд - основные функции
    builder.row(
        InlineKeyboardButton(
            text="💰 Заработать",
            callback_data=MainMenuCallback(action="earn").pack()
        ),
        InlineKeyboardButton(
            text="📢 Рекламировать", 
            callback_data=MainMenuCallback(action="advertise").pack()
        )
    )
    
    # Третий ряд - дополнительные функции
    builder.row(
        InlineKeyboardButton(
            text="✅ Проверка подписки",
            callback_data=MainMenuCallback(action="subscription_check").pack()
        ),
        InlineKeyboardButton(
            text="💳 Чеки",
            callback_data=MainMenuCallback(action="checks").pack()
        )
    )
    
    # Четвертый ряд - социальные функции
    builder.row(
        InlineKeyboardButton(
            text="🔗 Реферальная",
            callback_data=MainMenuCallback(action="referral").pack()
        ),
        InlineKeyboardButton(
            text="⚙️ Настройки",
            callback_data=MainMenuCallback(action="settings").pack()
        )
    )
    
    return builder.as_markup()

def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="🏠 В главное меню",
            callback_data=MainMenuCallback(action="main_menu").pack()
        )
    )
    return builder.as_markup()

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопка отмены"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel"
        )
    )
    return builder.as_markup()


