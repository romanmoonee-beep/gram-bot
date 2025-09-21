"""Клавиатуры для Telegram бота"""

from .main_menu import (
    MainMenuCallback,
    get_main_menu_keyboard,
    get_back_to_menu_keyboard,
    get_cancel_keyboard
)

from .profile import (
    ProfileCallback,
    get_profile_keyboard,
    get_deposit_keyboard
)

from .earn import (
    EarnCallback,
    get_earn_menu_keyboard,
    get_task_list_keyboard,
    get_task_view_keyboard,
    get_task_execution_keyboard
)

from .advertise import (
    AdvertiseCallback,
    get_advertise_menu_keyboard,
    get_my_tasks_keyboard,
    get_task_management_keyboard,
    get_task_type_keyboard
)

from .referral import (
    ReferralCallback,
    get_referral_keyboard,
    get_referral_link_keyboard
)

from .payments import (
    PaymentCallback,
    get_payment_confirmation_keyboard
)

__all__ = [
    # Main Menu
    "MainMenuCallback",
    "get_main_menu_keyboard",
    "get_back_to_menu_keyboard", 
    "get_cancel_keyboard",
    
    # Profile
    "ProfileCallback",
    "get_profile_keyboard",
    "get_deposit_keyboard",
    
    # Earn
    "EarnCallback",
    "get_earn_menu_keyboard",
    "get_task_list_keyboard",
    "get_task_view_keyboard",
    "get_task_execution_keyboard",
    
    # Advertise
    "AdvertiseCallback",
    "get_advertise_menu_keyboard",
    "get_my_tasks_keyboard",
    "get_task_management_keyboard",
    "get_task_type_keyboard",
    
    # Referral
    "ReferralCallback",
    "get_referral_keyboard",
    "get_referral_link_keyboard",
    
    # Payments
    "PaymentCallback",
    "get_payment_confirmation_keyboard"
]