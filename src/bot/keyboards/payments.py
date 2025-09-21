from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from app.config.settings import settings

class PaymentCallback(CallbackData, prefix="pay"):
    """Callback данные для платежей"""
    action: str
    package: str = "none"
    amount: int = 0

def get_payment_confirmation_keyboard(package_name: str, stars_amount: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения платежа"""
    builder = InlineKeyboardBuilder()
    
    # Кнопка оплаты Stars
    builder.row(
        InlineKeyboardButton(
            text=f"⭐ Оплатить {stars_amount} Stars",
            callback_data=PaymentCallback(action="confirm", package=package_name, amount=stars_amount).pack()
        )
    )
    
    # Отмена
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=MainMenuCallback(action="profile").pack()
        )
    )
    
    return builder.as_markup()
