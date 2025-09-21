from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from app.database.models.check import Check, CheckType
from app.database.models.user import User
from app.bot.keyboards.main_menu import MainMenuCallback

class CheckCallback(CallbackData, prefix="check"):
    """Callback данные для чеков"""
    action: str
    check_id: int = 0
    check_type: str = "none"
    page: int = 1

def get_checks_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню чеков"""
    builder = InlineKeyboardBuilder()
    
    # Создание чеков
    builder.row(
        InlineKeyboardButton(
            text="➕ Создать чек",
            callback_data=CheckCallback(action="create_menu").pack()
        )
    )
    
    # Управление чеками
    builder.row(
        InlineKeyboardButton(
            text="📋 Мои чеки",
            callback_data=CheckCallback(action="my_checks").pack()
        ),
        InlineKeyboardButton(
            text="💰 Активированные",
            callback_data=CheckCallback(action="activated").pack()
        )
    )
    
    # Активация чека
    builder.row(
        InlineKeyboardButton(
            text="🎫 Активировать чек",
            callback_data=CheckCallback(action="activate").pack()
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

def get_check_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа чека"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="👤 Персональный чек",
            callback_data=CheckCallback(action="create", check_type="personal").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="👥 Мульти-чек",
            callback_data=CheckCallback(action="create", check_type="multi").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🎁 Розыгрыш",
            callback_data=CheckCallback(action="create", check_type="giveaway").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=CheckCallback(action="menu").pack()
        )
    )
    
    return builder.as_markup()

def get_my_checks_keyboard(
    checks: list[Check], 
    page: int = 1,
    has_next: bool = False
) -> InlineKeyboardMarkup:
    """Клавиатура моих чеков"""
    builder = InlineKeyboardBuilder()
    
    # Чеки
    for check in checks:
        # Иконка статуса
        status_icons = {
            "active": "🟢",
            "expired": "⏰",
            "completed": "✅",
            "cancelled": "❌"
        }
        
        status_icon = status_icons.get(check.status, "❓")
        progress = f"{check.current_activations}/{check.max_activations}"
        
        button_text = f"{status_icon} #{check.check_code} | {progress}"
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=CheckCallback(action="manage", check_id=check.id).pack()
            )
        )
    
    # Навигация
    nav_buttons = []
    
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=CheckCallback(action="my_checks", page=page-1).pack()
            )
        )
    
    if has_next:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Вперед",
                callback_data=CheckCallback(action="my_checks", page=page+1).pack()
            )
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Кнопки управления
    builder.row(
        InlineKeyboardButton(
            text="➕ Создать новый",
            callback_data=CheckCallback(action="create_menu").pack()
        ),
        InlineKeyboardButton(
            text="🔄 Обновить",
            callback_data=CheckCallback(action="my_checks", page=page).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в чеки",
            callback_data=CheckCallback(action="menu").pack()
        )
    )
    
    return builder.as_markup()

def get_check_management_keyboard(check: Check) -> InlineKeyboardMarkup:
    """Клавиатура управления чеком"""
    builder = InlineKeyboardBuilder()
    
    # Поделиться чеком
    builder.row(
        InlineKeyboardButton(
            text="📤 Поделиться чеком",
            switch_inline_query=f"💳 Чек на {check.amount_per_activation:,.0f} GRAM! Код: {check.check_code}"
        )
    )
    
    # Копировать код
    builder.row(
        InlineKeyboardButton(
            text="📋 Скопировать код",
            callback_data=CheckCallback(action="copy_code", check_id=check.id).pack()
        )
    )
    
    # Аналитика
    builder.row(
        InlineKeyboardButton(
            text="📊 Аналитика",
            callback_data=CheckCallback(action="analytics", check_id=check.id).pack()
        )
    )
    
    # Отмена (только для активных чеков)
    if check.status == "active":
        builder.row(
            InlineKeyboardButton(
                text="❌ Отменить чек",
                callback_data=CheckCallback(action="cancel", check_id=check.id).pack()
            )
        )
    
    # Назад к списку
    builder.row(
        InlineKeyboardButton(
            text="⬅️ К моим чекам",
            callback_data=CheckCallback(action="my_checks").pack()
        )
    )
    
    return builder.as_markup()

def get_check_activation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура активации чека"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в чеки",
            callback_data=CheckCallback(action="menu").pack()
        )
    )
    
    return builder.as_markup()

def get_activated_checks_keyboard(
    activations: list,
    page: int = 1,
    has_next: bool = False
) -> InlineKeyboardMarkup:
    """Клавиатура активированных чеков"""
    builder = InlineKeyboardBuilder()
    
    # Навигация
    nav_buttons = []
    
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=CheckCallback(action="activated", page=page-1).pack()
            )
        )
    
    if has_next:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Вперед",
                callback_data=CheckCallback(action="activated", page=page+1).pack()
            )
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(
        InlineKeyboardButton(
            text="🔄 Обновить",
            callback_data=CheckCallback(action="activated", page=page).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в чеки",
            callback_data=CheckCallback(action="menu").pack()
        )
    )
    
    return builder.as_markup()

def get_check_display_keyboard(check_code: str) -> InlineKeyboardMarkup:
    """Клавиатура для отображения чека"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="💰 Активировать чек",
            callback_data=f"activate_check_{check_code}"
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
