from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from app.database.models.user import User
from app.database.models.task import TaskType
from app.services.task_service import TaskService
from app.bot.keyboards.earn import EarnCallback, get_earn_menu_keyboard, get_task_list_keyboard, get_task_view_keyboard, get_task_execution_keyboard
from app.bot.keyboards.main_menu import MainMenuCallback
from app.bot.utils.messages import get_task_list_text, get_task_text, get_task_execution_text, get_error_message, get_success_message

router = Router()

@router.message(Command("earn"))
async def cmd_earn(message: Message, user: User):
    """Команда /earn"""
    text = """💰 <b>ЗАРАБОТАТЬ GRAM</b>

Выберите тип заданий для выполнения:

🎯 <b>Доступные типы:</b>
• 📺 Подписка на каналы - простые задания
• 👥 Вступление в группы - быстрая награда  
• 👀 Просмотр постов - легкие задания
• 👍 Реакции на посты - мгновенная проверка
• 🤖 Переход в ботов - высокая награда

💎 <b>Ваш уровень:</b> {user.get_level_config()['name']}
⚡ <b>Множитель наград:</b> x{user.get_level_config()['task_multiplier']}

💡 <i>Чем выше ваш уровень, тем больше награда!</i>"""
    
    await message.answer(
        text,
        reply_markup=get_earn_menu_keyboard()
    )

@router.callback_query(MainMenuCallback.filter(F.action == "earn"))
async def show_earn_from_menu(callback: CallbackQuery, user: User):
    """Показать заработок из главного меню"""
    text = """💰 <b>ЗАРАБОТАТЬ GRAM</b>

Выберите тип заданий для выполнения:

🎯 <b>Доступные типы:</b>
• 📺 Подписка на каналы - простые задания
• 👥 Вступление в группы - быстрая награда  
• 👀 Просмотр постов - легкие задания
• 👍 Реакции на посты - мгновенная проверка
• 🤖 Переход в ботов - высокая награда

💎 <b>Ваш уровень:</b> {user.get_level_config()['name']}
⚡ <b>Множитель наград:</b> x{user.get_level_config()['task_multiplier']}

💡 <i>Чем выше ваш уровень, тем больше награда!</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_earn_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(EarnCallback.filter(F.action == "menu"))
async def show_earn_menu(callback: CallbackQuery, user: User):
    """Показать меню заработка"""
    text = """💰 <b>ЗАРАБОТАТЬ GRAM</b>

Выберите тип заданий для выполнения:

🎯 <b>Доступные типы:</b>
• 📺 Подписка на каналы - простые задания
• 👥 Вступление в группы - быстрая награда  
• 👀 Просмотр постов - легкие задания
• 👍 Реакции на посты - мгновенная проверка
• 🤖 Переход в ботов - высокая награда

💎 <b>Ваш уровень:</b> {user.get_level_config()['name']}
⚡ <b>Множитель наград:</b> x{user.get_level_config()['task_multiplier']}

💡 <i>Чем выше ваш уровень, тем больше награда!</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_earn_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(EarnCallback.filter(F.action == "list"))
async def show_task_list(
    callback: CallbackQuery, 
    callback_data: EarnCallback,
    user: User,
    task_service: TaskService
):
    """Показать список заданий"""
    task_type = None if callback_data.task_type == "all" else TaskType(callback_data.task_type)
    page = callback_data.page
    limit = 10
    offset = (page - 1) * limit
    
    try:
        # Получаем задания
        tasks = await task_service.get_available_tasks(
            user=user,
            task_type=task_type,
            limit=limit + 1,  # +1 для проверки наличия следующей страницы
            offset=offset
        )
        
        has_next = len(tasks) > limit
        if has_next:
            tasks = tasks[:limit]
        
        # Генерируем текст
        text = get_task_list_text(tasks, callback_data.task_type, page)
        
        # Генерируем клавиатуру
        keyboard = get_task_list_keyboard(tasks, callback_data.task_type, page, has_next)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error("Error loading tasks", error=str(e), user_id=user.telegram_id)
        await callback.answer("❌ Ошибка при загрузке заданий", show_alert=True)

@router.callback_query(EarnCallback.filter(F.action == "view"))
async def view_task(
    callback: CallbackQuery,
    callback_data: EarnCallback,
    user: User,
    task_service: TaskService
):
    """Просмотр конкретного задания"""
    try:
        task = await task_service.get_task_by_id(callback_data.task_id)
        
        if not task:
            await callback.answer(get_error_message("task_not_found"), show_alert=True)
            return
        
        # Проверяем доступность задания
        if not task.is_active:
            await callback.answer(get_error_message("task_not_active"), show_alert=True)
            return
        
        # Проверяем уровень пользователя
        if task.min_user_level:
            level_hierarchy = ["bronze", "silver", "gold", "premium"]
            if user.level not in level_hierarchy:
                await callback.answer("❌ Неизвестный уровень пользователя", show_alert=True)
                return
                
            required_index = level_hierarchy.index(task.min_user_level)
            user_index = level_hierarchy.index(user.level)
            
            if user_index < required_index:
                level_names = {
                    "bronze": "🥉 Bronze",
                    "silver": "🥈 Silver",
                    "gold": "🥇 Gold",
                    "premium": "💎 Premium"
                }
                required_level = level_names.get(task.min_user_level, task.min_user_level)
                await callback.answer(f"❌ Требуется уровень {required_level}", show_alert=True)
                return
        
        # Проверяем, не выполнял ли уже пользователь это задание
        user_executions = await task_service.get_user_executions(user.telegram_id, limit=1000)
        for execution in user_executions
