from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from decimal import Decimal

from app.database.models.user import User
from app.services.user_service import UserService
from app.services.task_service import TaskService
from app.services.transaction_service import TransactionService
from app.services.check_service import CheckService
from app.bot.keyboards.admin import (
    AdminCallback, get_admin_menu_keyboard, get_moderation_keyboard,
    get_task_moderation_keyboard, get_user_management_keyboard
)
from app.bot.keyboards.main_menu import get_main_menu_keyboard
from app.bot.states.admin_states import AdminStates
from app.bot.filters.admin import AdminFilter
from app.config.settings import settings

router = Router()
router.message.filter(AdminFilter())  # Только для админов
router.callback_query.filter(AdminFilter())

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Команда /admin"""
    text = """🔧 <b>АДМИН ПАНЕЛЬ</b>
    
Добро пожаловать в панель администратора!

🎯 <b>Доступные функции:</b>
• Модерация заданий и выполнений
• Управление пользователями
• Системная статистика
• Финансовая аналитика
• Системные функции"""
    
    await message.answer(
        text,
        reply_markup=get_admin_menu_keyboard()
    )

@router.callback_query(AdminCallback.filter(F.action == "menu"))
async def show_admin_menu(callback: CallbackQuery):
    """Показать главное меню админки"""
    text = """🔧 <b>АДМИН ПАНЕЛЬ</b>
    
Добро пожаловать в панель администратора!

🎯 <b>Доступные функции:</b>
• Модерация заданий и выполнений
• Управление пользователями
• Системная статистика
• Финансовая аналитика
• Системные функции"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(AdminCallback.filter(F.action == "moderation"))
async def show_moderation_menu(callback: CallbackQuery, task_service: TaskService):
    """Показать меню модерации"""
    
    # Получаем статистику заданий на модерации
    from app.database.models.task_execution import ExecutionStatus
    from sqlalchemy import select, func
    from app.database.database import get_session
    
    async with get_session() as session:
        # Количество выполнений ожидающих проверки
        pending_result = await session.execute(
            select(func.count()).select_from(
                session.query(TaskExecution).filter(
                    TaskExecution.status == ExecutionStatus.PENDING
                ).subquery()
            )
        )
        pending_count = pending_result.scalar() or 0
        
        # Количество заданий требующих ручной проверки
        manual_result = await session.execute(
            select(func.count()).select_from(
                session.query(TaskExecution).filter(
                    and_(
                        TaskExecution.status == ExecutionStatus.PENDING,
                        TaskExecution.auto_checked == False
                    )
                ).subquery()
            )
        )
        manual_count = manual_result.scalar() or 0
    
    text = f"""🔍 <b>МОДЕРАЦИЯ ЗАДАНИЙ</b>

📊 <b>СТАТИСТИКА:</b>
├ Ожидают проверки: {pending_count}
├ Ручная проверка: {manual_count}
├ Автопроверка: {pending_count - manual_count}
└ Всего активных: {pending_count}

⚡ <b>БЫСТРЫЕ ДЕЙСТВИЯ:</b>
• Просмотр заданий на проверке
• Массовое одобрение простых заданий
• Автообработка по критериям"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_moderation_keyboard()
    )
    await callback.answer()

@router.callback_query(AdminCallback.filter(F.action == "pending_tasks"))
async def show_pending_tasks(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    task_service: TaskService
):
    """Показать задания на проверке"""
    page = callback_data.page
    limit = 5
    offset = (page - 1) * limit
    
    # Получаем выполнения на проверке
    from app.database.models.task_execution import TaskExecution, ExecutionStatus
    from app.database.database import get_session
    from sqlalchemy import select, desc
    
    async with get_session() as session:
        result = await session.execute(
            select(TaskExecution)
            .where(TaskExecution.status == ExecutionStatus.PENDING)
            .order_by(desc(TaskExecution.created_at))
            .limit(limit + 1)
            .offset(offset)
        )
        
        executions = list(result.scalars().all())
        has_next = len(executions) > limit
        if has_next:
            executions = executions[:limit]
    
    if not executions:
        text = """🔍 <b>ЗАДАНИЯ НА ПРОВЕРКЕ</b>

✅ Все задания проверены!

📊 В очереди модерации заданий нет."""
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=AdminCallback(action="moderation").pack()
            )
        )
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()
        return
    
    text = f"""🔍 <b>ЗАДАНИЯ НА ПРОВЕРКЕ</b>

📄 Страница {page} | Всего: {len(executions)}

Выберите задание для модерации:"""
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    # Задания
    for execution in executions:
        task_title = execution.task.title[:30] + "..." if len(execution.task.title) > 30 else execution.task.title
        username = execution.user.username or f"ID{execution.user_id}"
        
        button_text = f"🎯 {task_title} | @{username}"
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=AdminCallback(action="review_task", target_id=execution.id).pack()
            )
        )
    
    # Навигация
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=AdminCallback(action="pending_tasks", page=page-1).pack()
            )
        )
    
    if has_next:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Вперед",
                callback_data=AdminCallback(action="pending_tasks", page=page+1).pack()
            )
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Массовые действия
    builder.row(
        InlineKeyboardButton(
            text="✅ Одобрить все автопроверки",
            callback_data=AdminCallback(action="approve_auto").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в модерацию",
            callback_data=AdminCallback(action="moderation").pack()
        )
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(AdminCallback.filter(F.action == "review_task"))
async def review_task_execution(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    task_service: TaskService
):
    """Детальный просмотр выполнения задания"""
    execution_id = callback_data.target_id
    
    from app.database.models.task_execution import TaskExecution
    from app.database.database import get_session
    from sqlalchemy import select
    
    async with get_session() as session:
        result = await session.execute(
            select(TaskExecution).where(TaskExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
    
    if not execution:
        await callback.answer("❌ Выполнение не найдено", show_alert=True)
        return
    
    task = execution.task
    user = execution.user
    
    # Проверяем автопроверку
    auto_check_text = "✅ Пройдена" if execution.auto_checked else "⏳ Требует проверки"
    
    text = f"""📋 <b>ПРОВЕРКА ВЫПОЛНЕНИЯ</b>

🎯 <b>ЗАДАНИЕ:</b>
├ Название: {task.title}
├ Тип: {task.type}
├ Автор: ID{task.author_id}
└ Награда: {execution.reward_amount:,.0f} GRAM

👤 <b>ИСПОЛНИТЕЛЬ:</b>
├ Пользователь: @{user.username or 'без username'}
├ ID: {user.telegram_id}
├ Уровень: {user.level}
└ Дата выполнения: {execution.created_at.strftime('%d.%m.%Y %H:%M')}

🔍 <b>ПРОВЕРКА:</b>
├ Автопроверка: {auto_check_text}
├ Ссылка: {task.target_url}
└ Статус: {execution.status}"""
    
    if execution.user_comment:
        text += f"\n\n💬 <b>Комментарий:</b>\n{execution.user_comment}"
    
    if execution.screenshot_url:
        text += f"\n\n📷 <b>Скриншот:</b> Прикреплен"
    
    keyboard = get_task_moderation_keyboard(execution.id)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(AdminCallback.filter(F.action == "approve"))
async def approve_task_execution(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    task_service: TaskService
):
    """Одобрить выполнение задания"""
    execution_id = callback_data.target_id
    
    success = await task_service.complete_task_execution(
        execution_id,
        auto_checked=False,
        reviewer_id=callback.from_user.id,
        review_comment="Одобрено администратором"
    )
    
    if success:
        await callback.answer("✅ Выполнение одобрено и оплачено")
        # Возвращаемся к списку
        await show_pending_tasks(
            callback,
            AdminCallback(action="pending_tasks", page=1),
            task_service
        )
    else:
        await callback.answer("❌ Не удалось одобрить выполнение", show_alert=True)

@router.callback_query(AdminCallback.filter(F.action == "reject"))
async def start_reject_task(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    state: FSMContext
):
    """Начать процесс отклонения задания"""
    execution_id = callback_data.target_id
    
    await state.set_state(AdminStates.entering_reject_reason)
    await state.update_data(execution_id=execution_id)
    
    text = """❌ <b>ОТКЛОНЕНИЕ ВЫПОЛНЕНИЯ</b>

Введите причину отклонения:

💡 <b>Примеры причин:</b>
• Задание не выполнено
• Недостаточно доказательств
• Нарушение условий
• Фальшивый скриншот

❌ <i>Для отмены отправьте /cancel</i>"""
    
    await callback.message.edit_text(text)
    await callback.answer()

@router.message(AdminStates.entering_reject_reason)
async def process_reject_reason(
    message: Message,
    state: FSMContext,
    task_service: TaskService
):
    """Обработать причину отклонения"""
    reason = message.text.strip()
    
    if len(reason) > 200:
        await message.answer("❌ Причина слишком длинная (максимум 200 символов)")
        return
    
    data = await state.get_data()
    execution_id = data['execution_id']
    
    # Отклоняем выполнение
    from app.database.models.task_execution import TaskExecution, ExecutionStatus
    from app.database.database import get_session
    from sqlalchemy import select
    
    async with get_session() as session:
        result = await session.execute(
            select(TaskExecution).where(TaskExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        
        if execution:
            execution.status = ExecutionStatus.REJECTED
            execution.reviewer_id = message.from_user.id
            execution.review_comment = reason
            execution.reviewed_at = datetime.utcnow()
            
            await session.commit()
    
    await state.clear()
    
    text = f"""✅ <b>ВЫПОЛНЕНИЕ ОТКЛОНЕНО</b>

Причина: {reason}

Пользователь будет уведомлен об отклонении."""
    
    await message.answer(
        text,
        reply_markup=get_admin_menu_keyboard()
    )

@router.callback_query(AdminCallback.filter(F.action == "users"))
async def show_user_management(callback: CallbackQuery, user_service: UserService):
    """Показать управление пользователями"""
    
    # Получаем статистику пользователей
    from app.database.database import get_session
    from app.database.models.user import User, UserLevel
    from sqlalchemy import select, func
    
    async with get_session() as session:
        # Общая статистика
        total_users = await session.execute(select(func.count(User.id)))
        total_count = total_users.scalar() or 0
        
        # По уровням
        levels_stats = await session.execute(
            select(User.level, func.count(User.id))
            .group_by(User.level)
        )
        
        levels_data = dict(levels_stats.fetchall())
        
        # Активные пользователи (были онлайн за последние 7 дней)
        from datetime import datetime, timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        active_users = await session.execute(
            select(func.count(User.id))
            .where(User.last_activity >= week_ago)
        )
        active_count = active_users.scalar() or 0
        
        # Заблокированные
        banned_users = await session.execute(
            select(func.count(User.id))
            .where(User.is_banned == True)
        )
        banned_count = banned_users.scalar() or 0
    
    text = f"""👥 <b>УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ</b>

📊 <b>ОБЩАЯ СТАТИСТИКА:</b>
├ Всего пользователей: {total_count:,}
├ Активных (7 дней): {active_count:,}
├ Заблокированных: {banned_count:,}
└ Конверсия активности: {(active_count/total_count*100 if total_count > 0 else 0):.1f}%

📈 <b>ПО УРОВНЯМ:</b>
├ 🥉 Bronze: {levels_data.get('bronze', 0):,}
├ 🥈 Silver: {levels_data.get('silver', 0):,}
├ 🥇 Gold: {levels_data.get('gold', 0):,}
└ 💎 Premium: {levels_data.get('premium', 0):,}

⚡ <b>ДЕЙСТВИЯ:</b>
• Поиск пользователя
• Управление балансом
• Блокировка/разблокировка
• Массовые рассылки"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_user_management_keyboard()
    )
    await callback.answer()

@router.callback_query(AdminCallback.filter(F.action == "find_user"))
async def start_find_user(callback: CallbackQuery, state: FSMContext):
    """Начать поиск пользователя"""
    
    await state.set_state(AdminStates.entering_user_id)
    
    text = """🔍 <b>ПОИСК ПОЛЬЗОВАТЕЛЯ</b>

Введите ID пользователя или username:

💡 <b>Примеры:</b>
• <code>123456789</code> (Telegram ID)
• <code>@username</code> (username)

❌ <i>Для отмены отправьте /cancel</i>"""
    
    await callback.message.edit_text(text)
    await callback.answer()

@router.message(AdminStates.entering_user_id)
async def process_find_user(
    message: Message,
    state: FSMContext,
    user_service: UserService
):
    """Обработать поиск пользователя"""
    query = message.text.strip()
    
    # Парсим запрос
    if query.startswith('@'):
        username = query[1:]
        # Поиск по username
        from app.database.database import get_session
        from sqlalchemy import select
        
        async with get_session() as session:
            result = await session.execute(
                select(User).where(User.username == username
