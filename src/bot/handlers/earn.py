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

💡 <i>Чем выше ваш уровень, тем больше награда!</i>"""
    
    await message.answer(
        text,
        reply_markup=get_earn_menu_keyboard()
    )

@router.callback_query(EarnCallback.filter(F.action == "menu"))
async def show_earn_menu(callback: CallbackQuery):
    """Показать меню заработка"""
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

@router.callback_query(EarnCallback.filter(F.action == "view"))
async def view_task(
    callback: CallbackQuery,
    callback_data: EarnCallback,
    user: User,
    task_service: TaskService
):
    """Просмотр конкретного задания"""
    task = await task_service.get_task_by_id(callback_data.task_id)
    
    if not task:
        await callback.answer(get_error_message("task_not_found"), show_alert=True)
        return
    
    # Проверяем доступность задания
    if not task.is_active:
        await callback.answer(get_error_message("task_not_active"), show_alert=True)
        return
    
    if not task.can_be_executed_by_user(user.level):
        await callback.answer(get_error_message("level_insufficient"), show_alert=True)
        return
    
    # Генерируем текст и клавиатуру
    text = get_task_text(task, user)
    keyboard = get_task_view_keyboard(task, user)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(EarnCallback.filter(F.action == "execute"))
async def execute_task(
    callback: CallbackQuery,
    callback_data: EarnCallback,
    user: User,
    task_service: TaskService
):
    """Начать выполнение задания"""
    task = await task_service.get_task_by_id(callback_data.task_id)
    
    if not task:
        await callback.answer(get_error_message("task_not_found"), show_alert=True)
        return
    
    # Создаем выполнение задания
    execution = await task_service.execute_task(
        task_id=task.id,
        user_id=user.telegram_id
    )
    
    if not execution:
        await callback.answer("❌ Не удалось начать выполнение задания", show_alert=True)
        return
    
    # Генерируем инструкции
    text = get_task_execution_text(task, user)
    keyboard = get_task_execution_keyboard(task)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer("✅ Выполнение задания начато!")

@router.callback_query(EarnCallback.filter(F.action == "check"))
async def check_task_execution(
    callback: CallbackQuery,
    callback_data: EarnCallback,
    user: User,
    task_service: TaskService
):
    """Проверить выполнение задания"""
    task = await task_service.get_task_by_id(callback_data.task_id)
    
    if not task:
        await callback.answer(get_error_message("task_not_found"), show_alert=True)
        return
    
    # Получаем выполнение пользователя
    executions = await task_service.get_user_executions(
        user.telegram_id,
        limit=1
    )
    
    execution = None
    for ex in executions:
        if ex.task_id == task.id and ex.status.value == "pending":
            execution = ex
            break
    
    if not execution:
        await callback.answer("❌ Выполнение не найдено", show_alert=True)
        return
    
    # Здесь должна быть логика проверки через Telegram API
    # Пока что автоматически засчитываем
    success = await task_service.complete_task_execution(
        execution.id,
        auto_checked=True
    )
    
    if success:
        user_config = user.get_level_config()
        final_reward = task.reward_amount * user_config['task_multiplier']
        
        success_text = f"""✅ <b>ЗАДАНИЕ ВЫПОЛНЕНО!</b>

🎯 {task.title}
💰 +{final_reward:,.0f} GRAM зачислено

🎉 Отлично! Продолжайте выполнять задания для увеличения заработка!"""
        
        from app.bot.keyboards.main_menu import get_main_menu_keyboard
        
        await callback.message.edit_text(
            success_text,
            reply_markup=get_main_menu_keyboard(user)
        )
        await callback.answer("🎉 Поздравляем с выполнением!")
    else:
        await callback.answer("❌ Проверка не пройдена", show_alert=True)

@router.callback_query(EarnCallback.filter(F.action == "info"))
async def show_task_info(
    callback: CallbackQuery,
    callback_data: EarnCallback,
    task_service: TaskService
):
    """Показать подробную информацию о задании"""
    task = await task_service.get_task_by_id(callback_data.task_id)
    
    if not task:
        await callback.answer(get_error_message("task_not_found"), show_alert=True)
        return
    
    # Получаем аналитику задания
    analytics = await task_service.get_task_analytics(task.id)
    
    info_text = f"""ℹ️ <b>ПОДРОБНАЯ ИНФОРМАЦИЯ</b>

🎯 <b>Задание:</b> {task.title}
👤 <b>Автор:</b> ID{task.author_id}
📅 <b>Создано:</b> {task.created_at.strftime('%d.%m.%Y %H:%M')}

📊 <b>ПРОГРЕСС:</b>
├ Выполнено: {task.completed_executions}/{task.target_executions}
├ Процент: {task.completion_percentage:.1f}%
└ Осталось: {task.remaining_executions}

💰 <b>НАГРАДЫ:</b>
├ За задание: {task.reward_amount:,.0f} GRAM
├ Потрачено: {task.spent_budget:,.0f} GRAM
└ Остается: {task.remaining_budget:,.0f} GRAM

⏱️ <b>ВРЕМЯ:</b>"""
    
    if task.expires_at:
        remaining = task.expires_at - task.created_at
        hours = int(remaining.total_seconds() // 3600)
        info_text += f"\n├ Осталось: {hours} часов"
    else:
        info_text += "\n├ Без ограничений по времени"
    
    if analytics and analytics.get('timing'):
        avg_time = analytics['timing']['average_seconds']
        info_text += f"\n└ Среднее время выполнения: {avg_time:.0f} сек"
    
    from app.bot.keyboards.earn import get_task_view_keyboard
    
    await callback.message.edit_text(
        info_text,
        reply_markup=get_task_view_keyboard(task, callback.from_user)
    )
    await callback.answer()

