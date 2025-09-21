from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from app.database.models.user import User
from app.bot.keyboards.main_menu import MainMenuCallback

class ProfileCallback(CallbackData, prefix="profile"):
    """Callback данные для профиля"""
    action: str
    data: str = "none"

def get_profile_keyboard(user: User) -> InlineKeyboardMarkup:
    """Клавиатура профиля пользователя"""
    builder = InlineKeyboardBuilder()
    
    # Первый ряд - пополнение
    builder.row(
        InlineKeyboardButton(
            text="💳 Пополнить баланс",
            callback_data=ProfileCallback(action="deposit").pack()
        )
    )
    
    # Второй ряд - детальная информация
    builder.row(
        InlineKeyboardButton(
            text="💰 Подробно о балансе",
            callback_data=ProfileCallback(action="balance").pack()
        ),
        InlineKeyboardButton(
            text="📊 Детальная статистика",
            callback_data=ProfileCallback(action="stats").pack()
        )
    )
    
    # Третий ряд - активность
    builder.row(
        InlineKeyboardButton(
            text="🎯 Мои задания",
            callback_data=ProfileCallback(action="my_tasks").pack()
        ),
        InlineKeyboardButton(
            text="💼 Выполненные задания",
            callback_data=ProfileCallback(action="executed_tasks").pack()
        )
    )
    
    # Четвертый ряд - рефералы и история
    builder.row(
        InlineKeyboardButton(
            text="👥 Мои рефералы",
            callback_data=ProfileCallback(action="referrals").pack()
        ),
        InlineKeyboardButton(
            text="📜 История транзакций",
            callback_data=ProfileCallback(action="transactions").pack()
        )
    )
    
    # Кнопка возврата
    builder.row(
        InlineKeyboardButton(
            text="🏠 В главное меню",
            callback_data=MainMenuCallback(action="main_menu").pack()
        )
    )
    
    return builder.as_markup()

def get_deposit_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для пополнения баланса"""
    from app.config.settings import settings
    
    builder = InlineKeyboardBuilder()
    
    # Пакеты Stars
    for package_name, package_data in settings.STARS_PACKAGES.items():
        stars = package_data["stars"]
        gram = package_data["gram"]
        bonus_text = ""
        
        if package_data.get("bonus_percent", 0) > 0:
            bonus_text = f" 💰 -{package_data['bonus_percent']}%"
        
        if package_data.get("bonus_gram", 0) > 0:
            bonus_text += f" +{package_data['bonus_gram']} GRAM"
        
        button_text = f"⭐ {stars} Stars → {gram:,} GRAM{bonus_text}"
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=ProfileCallback(action="buy_stars", data=package_name).pack()
            )
        )
    
    # Кнопка назад
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в профиль",
            callback_data=MainMenuCallback(action="profile").pack()
        )
    )
    
    return builder.as_markup()