from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from app.services.user_service import UserService
from app.bot.keyboards.main_menu import get_main_menu_keyboard, MainMenuCallback
from app.bot.utils.messages import get_main_menu_text

router = Router()

@router.callback_query(MainMenuCallback.filter(F.action == "main_menu"))
async def show_main_menu(
    callback: CallbackQuery, 
    callback_data: MainMenuCallback, 
    state: FSMContext,
    user_service: UserService
):
    """Показать главное меню"""
    await state.clear()
    
    user = await user_service.get_user(callback.from_user.id)
    menu_text = get_main_menu_text(user)
    
    await callback.message.edit_text(
        menu_text,
        reply_markup=get_main_menu_keyboard(user)
    )
    await callback.answer()

@router.message(F.text.in_(["🏠 Главное меню", "/menu"]))
async def main_menu_text(message: Message, state: FSMContext, user_service: UserService):
    """Главное меню по тексту кнопки"""
    await state.clear()
    
    user = await user_service.get_user(message.from_user.id)
    menu_text = get_main_menu_text(user)
    
    await message.answer(
        menu_text,
        reply_markup=get_main_menu_keyboard(user)
    )

# Обработка основных разделов меню
@router.callback_query(MainMenuCallback.filter(F.action == "earn"))
async def open_earn_section(callback: CallbackQuery):
    """Открыть раздел заработка"""
    from app.bot.keyboards.earn import get_earn_menu_keyboard
    from app.bot.utils.messages import get_task_list_text
    
    text = """💰 <b>ЗАРАБОТАТЬ GRAM</b>

Выберите тип заданий для выполнения:

🎯 <b>Доступные типы:</b>
• 📺 Подписка на каналы - простые задания
• 👥 Вступление в группы - быстрая награда  
• 👀 Просмотр постов - легкие задания
• 👍 Реакции на посты - мгновенная проверка
• 🤖 Переход в ботов - высокая награда

💡 <i>Чем выше ваш уровень, тем больше награда!</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_earn_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(MainMenuCallback.filter(F.action == "advertise"))
async def open_advertise_section(callback: CallbackQuery):
    """Открыть раздел рекламы"""
    from app.bot.keyboards.advertise import get_advertise_menu_keyboard
    
    text = """📢 <b>РЕКЛАМИРОВАТЬ</b>

Создавайте задания для продвижения ваших проектов:

🎯 <b>Типы заданий:</b>
• 📺 Подписка на канал - привлечение подписчиков
• 👥 Вступление в группу - рост сообщества
• 👀 Просмотр поста - увеличение охвата
• 👍 Реакция на пост - повышение активности
• 🤖 Переход в бота - привлечение пользователей

💰 <b>Комиссия:</b> от 3% до 7% в зависимости от уровня
⚡ <b>Результат:</b> быстрое выполнение заданий"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_advertise_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(MainMenuCallback.filter(F.action == "referral"))
async def open_referral_section(callback: CallbackQuery, user: User):
    """Открыть реферальную систему"""
    from app.bot.keyboards.referral import get_referral_keyboard
    from app.bot.utils.messages import get_referral_text
    
    text = get_referral_text(user)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_referral_keyboard()
    )
    await callback.answer()

# Заглушки для разделов в разработке
@router.callback_query(MainMenuCallback.filter(F.action == "checks"))
async def checks_placeholder(callback: CallbackQuery):
    """Заглушка для системы чеков"""
    await callback.answer("💳 Система чеков в разработке...", show_alert=True)

@router.callback_query(MainMenuCallback.filter(F.action == "subscription_check"))
async def subscription_check_placeholder(callback: CallbackQuery):
    """Заглушка для проверки подписок"""
    await callback.answer("✅ Проверка подписок в разработке...", show_alert=True)

@router.callback_query(MainMenuCallback.filter(F.action == "settings"))
async def settings_placeholder(callback: CallbackQuery):
    """Заглушка для настроек"""
    await callback.answer("⚙️ Настройки в разработке...", show_alert=True