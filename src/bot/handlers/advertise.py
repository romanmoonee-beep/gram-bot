from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.database.models.user import User
from app.database.models.task import TaskType, TaskStatus
from app.services.task_service import TaskService
from app.bot.keyboards.advertise import AdvertiseCallback, get_advertise_menu_keyboard, get_my_tasks_keyboard, get_task_management_keyboard
from app.bot.utils.messages import get_my_tasks_text, get_task_analytics_text, get_error_message, get_success_message
from app.bot.states.task_creation import TaskCreationStates

router = Router()

@router.message(Command("advertise"))
async def cmd_advertise(message: Message, user: User):
    """Команда /advertise"""
    text = """📢 <b>РЕКЛАМИРОВАТЬ</b>

Создавайте задания для продвижения ваших проектов:

🎯 <b>Типы заданий:</b>
• 📺 Подписка на канал - привлечение подписчиков
• 👥 Вступление в группу - рост сообщества
• 👀 Просмотр поста - увеличение охвата
• 👍 Реакция на пост - повышение активности
• 🤖 Переход в бота - привлечение пользователей

💰 <b>Ваша комиссия:</b> {user.get_level_config()['commission_rate']*100:.0f}%
⚡ <b>Результат:</b> быстрое выполнение заданий"""
    
    await message.answer(
        text,
        reply_markup=get_advertise_menu_keyboard()
    )

@router.callback_query(AdvertiseCallback.filter(F.action == "menu"))
async def show_advertise_menu(callback: CallbackQuery, user: User):
    """Показать меню рекламы"""
    text = """📢 <b>РЕКЛАМИРОВАТЬ</b>

Создавайте задания для продвижения ваших проектов:

🎯 <b>Типы заданий:</b>
• 📺 Подписка на канал - привлечение подписчиков
• 👥 Вступление в группу - рост сообщества
• 👀 Просмотр поста - увеличение охвата
• 👍 Реакция на пост - повышение активности
• 🤖 Переход в бота - привлечение пользователей

💰 <b>Ваша комиссия:</b> {user.get_level_config()['commission_rate']*100:.0f}%
⚡ <b>Результат:</b> быстрое выполнение заданий"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_advertise_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(AdvertiseCallback.filter(F.action == "my_tasks"))
async def show_my_tasks(
    callback: CallbackQuery,
    callback_data: AdvertiseCallback,
    user: User,
    task_service: TaskService
):
    """Показать мои задания"""
    page = callback_data.page
    limit = 10
    offset = (page - 1) * limit
    
    # Получаем задания пользователя
    tasks = await task_service.get_user_tasks(
        user.telegram_id,
        limit=limit + 1,
        offset=offset
    )
    
    has_next = len(tasks) > limit
    if has_next:
        tasks = tasks[:limit]
    
    text = get_my_tasks_text(tasks, page)
    keyboard = get_my_tasks_keyboard(tasks, page, has_next)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(AdvertiseCallback.filter(F.action == "manage"))
async def manage_task(
    callback: CallbackQuery,
    callback_data: AdvertiseCallback,
    task_service: TaskService
):
    """Управление заданием"""
    task = await task_service.get_task_by_id(callback_data.task_id)
    
    if not task:
        await callback.answer(get_error_message("task_not_found"), show_alert=True)
        return
    
    # Статус задания
    status_icons = {
        TaskStatus.ACTIVE: "🟢 Активное",
        TaskStatus.PAUSED: "⏸️ Приостановлено",
        TaskStatus.COMPLETED: "✅ Завершено",
        TaskStatus.CANCELLED: "❌ Отменено",
        TaskStatus.EXPIRED: "⏰ Истекло"
    }
    
    status_text = status_icons.get(task.status, "❓ Неизвестно")
    
    text = f"""🎯 <b>УПРАВЛЕНИЕ ЗАДАНИЕМ</b>

📋 <b>Название:</b> {task.title}
📊 <b>Статус:</b> {status_text}
💰 <b>Награда:</b> {task.reward_amount:,.0f} GRAM

📈 <b>ПРОГРЕСС:</b>
├ Выполнено: {task.completed_executions}/{task.target_executions}
├ Процент: {task.completion_percentage:.1f}%
└ Осталось: {task.remaining_executions}

💳 <b>БЮДЖЕТ:</b>
├ Общий: {task.total_budget:,.0f} GRAM
├ Потрачено: {task.spent_budget:,.0f} GRAM
└ Остается: {task.remaining_budget:,.0f} GRAM

📅 <b>Создано:</b> {task.created_at.strftime('%d.%m.%Y %H:%M')}"""
    
    if task.expires_at:
        text += f"\n⏰ <b>Истекает:</b> {task.expires_at.strftime('%d.%m.%Y %H:%M')}"
    
    keyboard = get_task_management_keyboard(task)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(AdvertiseCallback.filter(F.action == "pause"))
async def pause_task(
    callback: CallbackQuery,
    callback_data: AdvertiseCallback,
    user: User,
    task_service: TaskService
):
    """Приостановить задание"""
    success = await task_service.pause_task(callback_data.task_id, user.telegram_id)
    
    if success:
        await callback.answer("⏸️ Задание приостановлено")
        # Обновляем информацию о задании
        await manage_task(callback, callback_data, task_service)
    else:
        await callback.answer("❌ Не удалось приостановить задание", show_alert=True)

@router.callback_query(AdvertiseCallback.filter(F.action == "resume"))
async def resume_task(
    callback: CallbackQuery,
    callback_data: AdvertiseCallback,
    user: User,
    task_service: TaskService
):
    """Возобновить задание"""
    success = await task_service.resume_task(callback_data.task_id, user.telegram_id)
    
    if success:
        await callback.answer("▶️ Задание возобновлено")
        # Обновляем информацию о задании
        await manage_task(callback, callback_data, task_service)
    else:
        await callback.answer("❌ Не удалось возобновить задание", show_alert=True)

@router.callback_query(AdvertiseCallback.filter(F.action == "cancel"))
async def cancel_task(
    callback: CallbackQuery,
    callback_data: AdvertiseCallback,
    user: User,
    task_service: TaskService
):
    """Отменить задание"""
    # Подтверждение отмены
    text = """⚠️ <b>ОТМЕНА ЗАДАНИЯ</b>

Вы уверены, что хотите отменить задание?

💰 Неиспользованные средства будут возвращены на баланс.
❌ Это действие нельзя отменить."""
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Да, отменить",
            callback_data=AdvertiseCallback(action="cancel_confirm", task_id=callback_data.task_id).pack()
        ),
        InlineKeyboardButton(
            text="❌ Нет",
            callback_data=AdvertiseCallback(action="manage", task_id=callback_data.task_id).pack()
        )
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(AdvertiseCallback.filter(F.action == "cancel_confirm"))
async def cancel_task_confirm(
    callback: CallbackQuery,
    callback_data: AdvertiseCallback,
    user: User,
    task_service: TaskService
):
    """Подтверждение отмены задания"""
    success = await task_service.cancel_task(callback_data.task_id, user.telegram_id)
    
    if success:
        text = """✅ <b>ЗАДАНИЕ ОТМЕНЕНО</b>

Задание успешно отменено.
💰 Неиспользованные средства возвращены на баланс."""
        
        from app.bot.keyboards.main_menu import get_main_menu_keyboard
        
        await callback.message.edit_text(
            text,
            reply_markup=get_main_menu_keyboard(user)
        )
        await callback.answer("✅ Задание отменено")
    else:
        await callback.answer("❌ Не удалось отменить задание", show_alert=True)

@router.callback_query(AdvertiseCallback.filter(F.action == "analytics"))
async def show_task_analytics(
    callback: CallbackQuery,
    callback_data: AdvertiseCallback,
    task_service: TaskService
):
    """Показать аналитику задания"""
    analytics = await task_service.get_task_analytics(callback_data.task_id)
    
    if not analytics:
        await callback.answer("❌ Не удалось загрузить аналитику", show_alert=True)
        return
    
    text = get_task_analytics_text(analytics)
    
    # Добавляем статистику выполнений
    from app.bot.utils.messages import format_task_execution_stats
    stats_text = format_task_execution_stats(analytics['executions_by_status'])
    text += f"\n{stats_text}"
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к заданию",
            callback_data=AdvertiseCallback(action="manage", task_id=callback_data.task_id).pack()
        )
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# Обработчики создания заданий
@router.callback_query(AdvertiseCallback.filter(F.action == "create"))
async def start_task_creation(
    callback: CallbackQuery,
    callback_data: AdvertiseCallback,
    state: FSMContext,
    user: User
):
    """Начать создание задания"""
    # Проверяем возможность создания задания
    from app.bot.utils.messages import can_user_create_task, validate_reward_amount
    
    can_create, reason = can_user_create_task(user)
    if not can_create:
        await callback.answer(f"❌ {reason}", show_alert=True)
        return
    
    task_type = callback_data.task_type
    
    # Устанавливаем состояние создания задания
    await state.set_state(TaskCreationStates.entering_title)
    await state.update_data(task_type=task_type)
    
    # Названия типов заданий
    type_names = {
        "channel_subscription": "📺 Подписка на канал",
        "group_join": "👥 Вступление в группу",
        "post_view": "👀 Просмотр поста",
        "post_reaction": "👍 Реакция на пост",
        "bot_interaction": "🤖 Взаимодействие с ботом"
    }
    
    type_name = type_names.get(task_type, "Задание")
    
    text = f"""📝 <b>СОЗДАНИЕ ЗАДАНИЯ</b>

🎯 <b>Тип:</b> {type_name}

Введите название задания:

💡 <b>Рекомендации:</b>
• Используйте понятное название
• Укажите суть задания
• Минимум 5 символов

❌ <i>Для отмены отправьте /cancel</i>"""
    
    from app.bot.keyboards.main_menu import get_cancel_keyboard
    
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard())
    await callback.answer()

@router.message(TaskCreationStates.entering_title)
async def process_task_title(message: Message, state: FSMContext):
    """Обработка названия задания"""
    from app.bot.utils.messages import validate_task_title
    
    title = message.text.strip()
    
    # Валидация названия
    is_valid, error = validate_task_title(title)
    if not is_valid:
        await message.answer(f"❌ {error}\n\nПопробуйте еще раз:")
        return
    
    # Сохраняем название и переходим к описанию
    await state.update_data(title=title)
    await state.set_state(TaskCreationStates.entering_description)
    
    text = f"""📝 <b>СОЗДАНИЕ ЗАДАНИЯ</b>

✅ <b>Название:</b> {title}

Теперь введите описание задания:

💡 <b>Рекомендации:</b>
• Опишите, что нужно сделать
• Укажите дополнительные требования
• Максимум 500 символов

❌ <i>Для отмены отправьте /cancel</i>"""
    
    await message.answer(text)

@router.message(TaskCreationStates.entering_description)
async def process_task_description(message: Message, state: FSMContext):
    """Обработка описания задания"""
    description = message.text.strip()
    
    if len(description) > 500:
        await message.answer("❌ Описание слишком длинное (максимум 500 символов)\n\nПопробуйте еще раз:")
        return
    
    # Сохраняем описание и переходим к URL
    await state.update_data(description=description)
    await state.set_state(TaskCreationStates.entering_url)
    
    data = await state.get_data()
    task_type = data["task_type"]
    
    # Инструкции для разных типов заданий
    url_instructions = {
        "channel_subscription": "Введите ссылку на канал (например: @channel или https://t.me/channel):",
        "group_join": "Введите ссылку на группу (например: @group или https://t.me/group):",
        "post_view": "Введите ссылку на пост (например: https://t.me/channel/123):",
        "post_reaction": "Введите ссылку на пост для реакции:",
        "bot_interaction": "Введите ссылку на бота (например: @bot или https://t.me/bot):"
    }
    
    instruction = url_instructions.get(task_type, "Введите ссылку:")
    
    text = f"""📝 <b>СОЗДАНИЕ ЗАДАНИЯ</b>

✅ <b>Название:</b> {data['title']}
✅ <b>Описание:</b> {description[:50]}...

{instruction}

💡 <b>Форматы ссылок:</b>
• @username
• https://t.me/username
• https://t.me/username/123 (для постов)

❌ <i>Для отмены отправьте /cancel</i>"""
    
    await message.answer(text)

@router.message(TaskCreationStates.entering_url)
async def process_task_url(message: Message, state: FSMContext):
    """Обработка URL задания"""
    from app.bot.utils.messages import validate_url
    
    url = message.text.strip()
    
    # Валидация URL
    if not validate_url(url):
        await message.answer("❌ Некорректная ссылка\n\nПопробуйте еще раз:")
        return
    
    # Сохраняем URL и переходим к награде
    await state.update_data(target_url=url)
    await state.set_state(TaskCreationStates.entering_reward)
    
    data = await state.get_data()
    
    text = f"""📝 <b>СОЗДАНИЕ ЗАДАНИЯ</b>

✅ <b>Название:</b> {data['title']}
✅ <b>Описание:</b> {data['description'][:50]}...
✅ <b>Ссылка:</b> {url}

Введите награду за выполнение (в GRAM):

💡 <b>Рекомендации:</b>
• Минимум: 50 GRAM
• Чем больше награда, тем быстрее выполнение
• Учитывайте комиссию при расчете бюджета

❌ <i>Для отмены отправьте /cancel</i>"""
    
    await message.answer(text)

@router.message(TaskCreationStates.entering_reward)
async def process_task_reward(message: Message, state: FSMContext, user: User):
    """Обработка награды за задание"""
    from decimal import Decimal, InvalidOperation
    from app.bot.utils.messages import validate_reward_amount
    
    try:
        reward = Decimal(message.text.strip())
    except (InvalidOperation, ValueError):
        await message.answer("❌ Введите корректное число\n\nПопробуйте еще раз:")
        return
    
    # Валидация суммы награды
    is_valid, error = validate_reward_amount(reward, user.level)
    if not is_valid:
        await message.answer(f"❌ {error}\n\nПопробуйте еще раз:")
        return
    
    # Сохраняем награду и переходим к количеству
    await state.update_data(reward_amount=reward)
    await state.set_state(TaskCreationStates.entering_quantity)
    
    data = await state.get_data()
    
    text = f"""📝 <b>СОЗДАНИЕ ЗАДАНИЯ</b>

✅ <b>Название:</b> {data['title']}
✅ <b>Описание:</b> {data['description'][:50]}...
✅ <b>Ссылка:</b> {data['target_url']}
✅ <b>Награда:</b> {reward:,.0f} GRAM

Введите количество выполнений:

💡 <b>Рекомендации:</b>
• Минимум: 1 выполнение
• Максимум: 10,000 выполнений
• Учитывайте свой бюджет

❌ <i>Для отмены отправьте /cancel</i>"""
    
    await message.answer(text)

@router.message(TaskCreationStates.entering_quantity)
async def process_task_quantity(message: Message, state: FSMContext, user: User, task_service: TaskService):
    """Обработка количества выполнений"""
    try:
        quantity = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите корректное число\n\nПопробуйте еще раз:")
        return
    
    if quantity < 1 or quantity > 10000:
        await message.answer("❌ Количество должно быть от 1 до 10,000\n\nПопробуйте еще раз:")
        return
    
    # Получаем данные и рассчитываем бюджет
    data = await state.get_data()
    reward = data["reward_amount"]
    
    # Рассчитываем общий бюджет
    user_config = user.get_level_config()
    commission_rate = user_config["commission_rate"]
    
    total_reward = reward * quantity
    commission = total_reward * commission_rate
    total_budget = total_reward + commission
    
    # Проверяем баланс
    if user.available_balance < total_budget:
        await message.answer(
            f"❌ Недостаточно средств\n\n"
            f"💰 Требуется: {total_budget:,.0f} GRAM\n"
            f"💳 Доступно: {user.available_balance:,.0f} GRAM\n\n"
            f"Пополните баланс или уменьшите параметры задания."
        )
        return
    
    # Переходим к подтверждению
    await state.update_data(target_executions=quantity)
    await state.set_state(TaskCreationStates.confirmation)
    
    text = f"""✅ <b>ПОДТВЕРЖДЕНИЕ СОЗДАНИЯ</b>

📋 <b>ЗАДАНИЕ:</b>
├ Название: {data['title']}
├ Описание: {data['description']}
├ Ссылка: {data['target_url']}
├ Награда: {reward:,.0f} GRAM
└ Количество: {quantity}

💰 <b>БЮДЖЕТ:</b>
├ Награды: {total_reward:,.0f} GRAM
├ Комиссия ({commission_rate*100:.0f}%): {commission:,.0f} GRAM
└ Итого: {total_budget:,.0f} GRAM

💳 <b>Ваш баланс:</b> {user.balance:,.0f} GRAM
💳 <b>Останется:</b> {user.balance - total_budget:,.0f} GRAM"""
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Создать задание",
            callback_data="create_task_confirm"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel"
        )
    )
    
    await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "create_task_confirm")
async def create_task_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    task_service: TaskService
):
    """Подтверждение создания задания"""
    data = await state.get_data()
    
    # Создаем задание
    task = await task_service.create_task(
        author_id=user.telegram_id,
        task_type=TaskType(data["task_type"]),
        title=data["title"],
        description=data["description"],
        target_url=data["target_url"],
        reward_amount=data["reward_amount"],
        target_executions=data["target_executions"]
    )
    
    if task:
        text = f"""🎉 <b>ЗАДАНИЕ СОЗДАНО!</b>

🎯 {task.title}
💰 {task.reward_amount:,.0f} GRAM за выполнение
👥 Цель: {task.target_executions} выполнений

📊 ID задания: #{task.id}
✅ Статус: Активное
🚀 Ваше задание уже показывается пользователям!

💡 Отслеживайте прогресс в разделе "📢 Рекламировать" → "🎯 Мои задания" """
        
        from app.bot.keyboards.main_menu import get_main_menu_keyboard
        
        await callback.message.edit_text(
            text,
            reply_markup=get_main_menu_keyboard(user)
        )
        await callback.answer("🎉 Задание успешно создано!")
    else:
        await callback.answer("❌ Не удалось создать задание", show_alert=True)
    
    # Очищаем состояние
    await state.clear()