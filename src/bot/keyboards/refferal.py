from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from app.database.models.user import User
from app.bot.keyboards.main_menu import MainMenuCallback

class ReferralCallback(CallbackData, prefix="ref"):
    """Callback данные для реферальной системы"""
    action: str
    page: int = 1

def get_referral_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура реферальной системы"""
    builder = InlineKeyboardBuilder()
    
    # Основные действия
    builder.row(
        InlineKeyboardButton(
            text="🔗 Моя ссылка",
            callback_data=ReferralCallback(action="link").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="👥 Мои рефералы",
            callback_data=ReferralCallback(action="list").pack()
        ),
        InlineKeyboardButton(
            text="💰 Доходы",
            callback_data=ReferralCallback(action="earnings").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="📊 Статистика",
            callback_data=ReferralCallback(action="stats").pack()
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

def get_referral_link_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура реферальной ссылки"""
    builder = InlineKeyboardBuilder()
    
    # Поделиться ссылкой
    referral_link = f"https://t.me/{settings.BOT_USERNAME}?start={user_id}"
    
    builder.row(
        InlineKeyboardButton(
            text="📤 Поделиться ссылкой",
            switch_inline_query=f"🤖 Присоединяйся к PR GRAM Bot и зарабатывай GRAM! {referral_link}"
        )
    )
    
    # Копировать ссылку (через URL)
    builder.row(
        InlineKeyboardButton(
            text="📋 Копировать ссылку",
            url=f"https://t.me/share/url?url={referral_link}&text=Присоединяйся к PR GRAM Bot!"
        )
    )
    
    # Назад
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=ReferralCallback(action="menu").pack()
        )
    )
    
    return builder.as_markup(