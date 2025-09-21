from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.bot.keyboards.main_menu import get_main_menu_keyboard
from app.bot.utils.messages import get_main_menu_text

router = Router()

@router.message(F.text.in_(["❌ Отмена", "/cancel"]))
async def cancel_action(message: Message, state: FSMContext, user: User):
    """Отмена текущего действия"""
    await state.clear()
    
    menu_text = get_main_menu_text(user)
    
    await message.answer(
        f"❌ Действие отменено\n\n{menu_text}",
        reply_markup=get_main_menu_keyboard(user)
    )

@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext, user: User):
    """Отмена через callback"""
    await state.clear()
    
    menu_text = get_main_menu_text(user)
    
    await callback.message.edit_text(
        f"❌ Действие отменено\n\n{menu_text}",
        reply_markup=get_main_menu_keyboard(user)
    )
    await callback.answer()

@router.message()
async def unknown_message(message: Message, user: User):
    """Обработчик неизвестных сообщений"""
    response_text = """❓ Я не понимаю эту команду.

Используйте кнопки меню ниже или команды:
/start - главное меню
/help - помощь
/profile - мой профиль
/earn - заработать
/advertise - рекламировать"""
    
    await message.answer(
        response_text,
        reply_markup=get_main_menu_keyboard(user)
    )

@router.callback_query()
async def unknown_callback(callback: CallbackQuery):
    """Обработчик неизвестных callback'ов"""
    await callback.answer("❓ Неизвестная команда", show_alert=True
    )