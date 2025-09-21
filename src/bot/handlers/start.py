from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from app.services.user_service import UserService
from app.bot.keyboards.main_menu import get_main_menu_keyboard
from app.bot.utils.messages import get_welcome_text, HELP_MESSAGE, get_main_menu_text

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, user_service: UserService):
    """Обработка команды /start"""
    # Очищаем состояние
    await state.clear()
    
    # Извлекаем реферальный код из команды
    args = message.text.split()
    referrer_id = None
    
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
        except ValueError:
            pass
    
    # Создаем или получаем пользователя
    user = await user_service.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        referrer_id=referrer_id
    )
    
    # Отправляем приветственное сообщение
    welcome_text = get_welcome_text(user)
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(user)
    )

@router.message(Command("help"))
async def cmd_help(message: Message, user_service: UserService):
    """Обработка команды /help"""
    user = await user_service.get_user(message.from_user.id)
    
    await message.answer(
        HELP_MESSAGE,
        reply_markup=get_main_menu_keyboard(user)
    )

@router.message(Command("menu"))
async def cmd_menu(message: Message, user_service: UserService):
    """Обработка команды /menu"""
    user = await user_service.get_user(message.from_user.id)
    menu_text = get_main_menu_text(user)
    
    await message.answer(
        menu_text,
        reply_markup=get_main_menu_keyboard(user)
    )
