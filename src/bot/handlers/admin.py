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
        user = await user_service.get_user_by_username(username)
    else:
        try:
            user_id = int(query)
            user = await user_service.get_user(user_id)
        except ValueError:
            await message.answer("❌ Некорректный ID или username")
            return
    
    if not user:
        await message.answer("❌ Пользователь не найден")
        return
    
    # Показываем информацию о пользователе
    text = f"""👤 <b>ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ</b>

🆔 ID: <code>{user.telegram_id}</code>
👤 Username: @{user.username or 'не указан'}
📝 Имя: {user.first_name or 'не указано'}
💰 Баланс: {user.balance:,.0f} GRAM
📊 Уровень: {user.level}
📅 Регистрация: {user.created_at.strftime('%d.%m.%Y')}

📈 <b>СТАТИСТИКА:</b>
├ Заданий выполнено: {user.tasks_completed}
├ Заданий создано: {user.tasks_created}
├ Рефералов: {user.total_referrals}
└ Статус: {'🚫 Заблокирован' if user.is_banned else '✅ Активен'}"""
    
    await message.answer(text)
    await state.clear()
    
    # Статистика пользователя
    stats = await user_service.get_user_stats(user.telegram_id)
    
    status_text = "✅ Активен"
    if user.is_banned:
        status_text = f"❌ Заблокирован: {user.ban_reason}"
    
    text = f"""👤 <b>ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ</b>

🆔 <b>ОСНОВНОЕ:</b>
├ ID: <code>{user.telegram_id}</code>
├ Username: @{user.username or 'не указан'}
├ Имя: {user.full_name}
├ Статус: {status_text}
└ Уровень: {user.get_level_config()['name']}

💰 <b>ФИНАНСЫ:</b>
├ Баланс: {user.balance:,.0f} GRAM
├ Заморожено: {user.frozen_balance:,.0f} GRAM
├ Заработано: {user.total_earned:,.0f} GRAM
└ Потрачено: {user.total_spent:,.0f} GRAM

📊 <b>АКТИВНОСТЬ:</b>
├ Заданий выполнено: {user.tasks_completed}
├ Заданий создано: {user.tasks_created}
├ Рефералов: {user.total_referrals}
├ Транзакций: {stats['total_transactions']}
└ Возраст аккаунта: {stats['account_age_days']} дн.

📅 <b>ДАТЫ:</b>
├ Регистрация: {user.created_at.strftime('%d.%m.%Y %H:%M')}
└ Последняя активность: {user.last_activity.strftime('%d.%m.%Y %H:%M') if user.last_activity else 'давно'}"""
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    # Действия с пользователем
    if not user.is_banned:
        builder.row(
            InlineKeyboardButton(
                text="🚫 Заблокировать",
                callback_data=AdminCallback(action="ban_user", target_id=user.telegram_id).pack()
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="✅ Разблокировать",
                callback_data=AdminCallback(action="unban_user", target_id=user.telegram_id).pack()
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="💰 Изменить баланс",
            callback_data=AdminCallback(action="change_balance", target_id=user.telegram_id).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="📊 Подробная статистика",
            callback_data=AdminCallback(action="user_details", target_id=user.telegram_id).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к управлению",
            callback_data=AdminCallback(action="users").pack()
        )
    )
    
    await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(AdminCallback.filter(F.action == "ban_user"))
async def start_ban_user(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    state: FSMContext
):
    """Начать блокировку пользователя"""
    
    user_id = callback_data.target_id
    await state.set_state(AdminStates.entering_ban_reason)
    await state.update_data(user_id=user_id)
    
    text = """🚫 <b>БЛОКИРОВКА ПОЛЬЗОВАТЕЛЯ</b>

Введите причину блокировки:

💡 <b>Примеры причин:</b>
• Мошенничество
• Нарушение правил
• Спам
• Фейковая активность

❌ <i>Для отмены отправьте /cancel</i>"""
    
    await callback.message.edit_text(text)
    await callback.answer()

@router.message(AdminStates.entering_ban_reason)
async def process_ban_user(
    message: Message,
    state: FSMContext,
    user_service: UserService
):
    """Обработать блокировку пользователя"""
    reason = message.text.strip()
    
    if len(reason) > 200:
        await message.answer("❌ Причина слишком длинная (максимум 200 символов)")
        return
    
    data = await state.get_data()
    user_id = data['user_id']
    
    success = await user_service.ban_user(
        user_id,
        reason,
        message.from_user.id
    )
    
    await state.clear()
    
    if success:
        text = f"""✅ <b>ПОЛЬЗОВАТЕЛЬ ЗАБЛОКИРОВАН</b>

ID: {user_id}
Причина: {reason}

Пользователь больше не сможет пользоваться ботом."""
    else:
        text = "❌ Не удалось заблокировать пользователя"
    
    await message.answer(
        text,
        reply_markup=get_admin_menu_keyboard()
    )

@router.callback_query(AdminCallback.filter(F.action == "unban_user"))
async def unban_user(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    user_service: UserService
):
    """Разблокировать пользователя"""
    
    user_id = callback_data.target_id
    
    success = await user_service.unban_user(user_id, callback.from_user.id)
    
    if success:
        await callback.answer("✅ Пользователь разблокирован")
        text = f"""✅ <b>ПОЛЬЗОВАТЕЛЬ РАЗБЛОКИРОВАН</b>

ID: {user_id}

Пользователь снова может пользоваться ботом."""
    else:
        await callback.answer("❌ Не удалось разблокировать", show_alert=True)
        return
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_menu_keyboard()
    )

@router.callback_query(AdminCallback.filter(F.action == "stats"))
async def show_system_stats(callback: CallbackQuery):
    """Показать системную статистику"""
    
    from app.database.database import get_session
    from app.database.models.user import User
    from app.database.models.task import Task, TaskStatus
    from app.database.models.task_execution import TaskExecution, ExecutionStatus
    from app.database.models.transaction import Transaction
    from sqlalchemy import select, func
    from datetime import datetime, timedelta
    
    async with get_session() as session:
        # Статистика пользователей
        users_total = await session.execute(select(func.count(User.id)))
        users_count = users_total.scalar() or 0
        
        # Статистика заданий
        tasks_stats = await session.execute(
            select(Task.status, func.count(Task.id))
            .group_by(Task.status)
        )
        tasks_by_status = dict(tasks_stats.fetchall())
        
        # Статистика выполнений
        executions_stats = await session.execute(
            select(TaskExecution.status, func.count(TaskExecution.id))
            .group_by(TaskExecution.status)
        )
        executions_by_status = dict(executions_stats.fetchall())
        
        # Финансовая статистика
        total_gram = await session.execute(
            select(func.sum(User.balance))
        )
        total_balance = total_gram.scalar() or 0
        
        # Транзакции за 24 часа
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_transactions = await session.execute(
            select(func.count(Transaction.id))
            .where(Transaction.created_at >= yesterday)
        )
        recent_tx_count = recent_transactions.scalar() or 0
        
        # Новые пользователи за 24 часа
        new_users = await session.execute(
            select(func.count(User.id))
            .where(User.created_at >= yesterday)
        )
        new_users_count = new_users.scalar() or 0
    
    text = f"""📊 <b>СИСТЕМНАЯ СТАТИСТИКА</b>

👥 <b>ПОЛЬЗОВАТЕЛИ:</b>
├ Всего: {users_count:,}
├ Новых за 24ч: {new_users_count:,}
└ Рост: {(new_users_count/users_count*100 if users_count > 0 else 0):.2f}%

🎯 <b>ЗАДАНИЯ:</b>
├ Активных: {tasks_by_status.get('active', 0):,}
├ Завершенных: {tasks_by_status.get('completed', 0):,}
├ Приостановленных: {tasks_by_status.get('paused', 0):,}
└ Отмененных: {tasks_by_status.get('cancelled', 0):,}

💼 <b>ВЫПОЛНЕНИЯ:</b>
├ Ожидают: {executions_by_status.get('pending', 0):,}
├ Завершены: {executions_by_status.get('completed', 0):,}
├ Отклонены: {executions_by_status.get('rejected', 0):,}
└ Просрочены: {executions_by_status.get('expired', 0):,}

💰 <b>ФИНАНСЫ:</b>
├ Общий баланс: {total_balance:,.0f} GRAM
├ Транзакций за 24ч: {recent_tx_count:,}
└ Средний баланс: {(total_balance/users_count if users_count > 0 else 0):,.0f} GRAM

🕐 <b>Последнее обновление:</b> {datetime.utcnow().strftime('%d.%m.%Y %H:%M')}"""
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="💰 Финансовая статистика",
            callback_data=AdminCallback(action="finance_stats").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🔄 Обновить данные",
            callback_data=AdminCallback(action="stats").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в админку",
            callback_data=AdminCallback(action="menu").pack()
        )
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(AdminCallback.filter(F.action == "finance_stats"))
async def show_finance_stats(callback: CallbackQuery, transaction_service: TransactionService):
    """Показать финансовую статистику"""
    
    from app.database.database import get_session
    from app.database.models.transaction import Transaction, TransactionType
    from sqlalchemy import select, func
    from datetime import datetime, timedelta
    
    async with get_session() as session:
        # Статистика по типам транзакций
        tx_types_stats = await session.execute(
            select(
                Transaction.type,
                func.count(Transaction.id).label('count'),
                func.sum(Transaction.amount).label('total')
            )
            .group_by(Transaction.type)
        )
        
        # Статистика за последние 7 дней
        week_ago = datetime.utcnow() - timedelta(days=7)
        weekly_stats = await session.execute(
            select(
                func.sum(Transaction.amount).filter(Transaction.amount > 0).label('income'),
                func.sum(Transaction.amount).filter(Transaction.amount < 0).label('spending'),
                func.count(Transaction.id).label('total_tx')
            )
            .where(Transaction.created_at >= week_ago)
        )
        
        weekly = weekly_stats.first()
        
        # ТОП пользователей по балансу
        top_users = await session.execute(
            select(User.telegram_id, User.username, User.balance)
            .order_by(User.balance.desc())
            .limit(5)
        )
        
        # Статистика Stars платежей
        stars_stats = await session.execute(
            select(
                func.count(Transaction.id).label('count'),
                func.sum(Transaction.amount).label('total_gram'),
                func.sum(Transaction.stars_amount).label('total_stars')
            )
            .where(Transaction.type == TransactionType.DEPOSIT_STARS)
        )
        
        stars = stars_stats.first()
    
    # Формируем статистику по типам
    types_text = ""
    for row in tx_types_stats:
        tx_type = row.type
        count = row.count
        total = row.total or 0
        
        type_names = {
            'deposit_stars': '⭐ Stars',
            'task_reward': '🎯 Награды',
            'task_creation': '📢 Создание',
            'referral_bonus': '👥 Рефералы'
        }
        
        name = type_names.get(tx_type, tx_type)
        types_text += f"├ {name}: {count:,} шт. | {total:,.0f} GRAM\n"
    
    text = f"""💰 <b>ФИНАНСОВАЯ СТАТИСТИКА</b>

📊 <b>ЗА НЕДЕЛЮ:</b>
├ Доходы: +{float(weekly.income or 0):,.0f} GRAM
├ Расходы: {float(weekly.spending or 0):,.0f} GRAM
├ Транзакций: {weekly.total_tx:,}
└ Прибыль: {float((weekly.income or 0) + (weekly.spending or 0)):,.0f} GRAM

🌟 <b>TELEGRAM STARS:</b>
├ Платежей: {stars.count or 0:,}
├ Получено GRAM: {float(stars.total_gram or 0):,.0f}
└ Получено Stars: {stars.total_stars or 0:,}

📈 <b>ПО ТИПАМ ТРАНЗАКЦИЙ:</b>
{types_text}

🏆 <b>ТОП ПОЛЬЗОВАТЕЛЕЙ:</b>"""
    
    for i, user in enumerate(top_users, 1):
        username = user.username or f"ID{user.telegram_id}"
        text += f"\n{i}. @{username}: {user.balance:,.0f} GRAM"
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="📊 Детальная аналитика",
            callback_data=AdminCallback(action="detailed_analytics").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к статистике",
            callback_data=AdminCallback(action="stats").pack()
        )
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(AdminCallback.filter(F.action == "system"))
async def show_system_functions(callback: CallbackQuery):
    """Показать системные функции"""
    
    text = """⚙️ <b>СИСТЕМНЫЕ ФУНКЦИИ</b>

🛠️ <b>ДОСТУПНЫЕ ДЕЙСТВИЯ:</b>
• Очистка истекших чеков
• Очистка истекших заданий
• Обновление уровней пользователей
• Массовая рассылка
• Резервное копирование

⚠️ <b>ВНИМАНИЕ:</b>
Системные функции влияют на всех пользователей!
Используйте осторожно."""
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🧹 Очистить истекшие",
            callback_data=AdminCallback(action="cleanup").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="📢 Массовая рассылка",
            callback_data=AdminCallback(action="broadcast").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬆️ Обновить уровни",
            callback_data=AdminCallback(action="update_levels").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в админку",
            callback_data=AdminCallback(action="menu").pack()
        )
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(AdminCallback.filter(F.action == "cleanup"))
async def system_cleanup(
    callback: CallbackQuery,
    check_service: CheckService,
    task_service: TaskService
):
    """Системная очистка"""
    
    # Очистка истекших чеков
    expired_checks = await check_service.cleanup_expired_checks()
    
    # Здесь можно добавить очистку других элементов
    
    text = f"""🧹 <b>СИСТЕМНАЯ ОЧИСТКА ЗАВЕРШЕНА</b>

📊 <b>РЕЗУЛЬТАТЫ:</b>
├ Истекших чеков удалено: {expired_checks}
├ Истекших заданий: 0 (функция в разработке)
└ Освобождено средств: автоматически

✅ Система очищена от устаревших данных."""
    
    await callback.answer("🧹 Очистка выполнена")
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_menu_keyboard()
    )

# Массовые действия
@router.callback_query(AdminCallback.filter(F.action == "approve_auto"))
async def mass_approve_auto_checks(
    callback: CallbackQuery,
    task_service: TaskService
):
    """Массовое одобрение автопроверок"""
    
    from app.database.database import get_session
    from app.database.models.task_execution import TaskExecution, ExecutionStatus
    from sqlalchemy import select, and_
    
    approved_count = 0
    
    async with get_session() as session:
        # Находим все автопроверенные выполнения
        result = await session.execute(
            select(TaskExecution).where(
                and_(
                    TaskExecution.status == ExecutionStatus.PENDING,
                    TaskExecution.auto_checked == True
                )
            )
        )
        
        auto_executions = list(result.scalars().all())
        
        for execution in auto_executions:
            success = await task_service.complete_task_execution(
                execution.id,
                auto_checked=True,
                reviewer_id=callback.from_user.id,
                review_comment="Массовое одобрение автопроверок"
            )
            
            if success:
                approved_count += 1
    
    text = f"""✅ <b>МАССОВОЕ ОДОБРЕНИЕ ЗАВЕРШЕНО</b>

📊 Одобрено автопроверок: {approved_count}

Все задания с успешной автопроверкой были одобрены и оплачены."""
    
    await callback.answer(f"✅ Одобрено {approved_count} заданий")
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_menu_keyboard()
    )
