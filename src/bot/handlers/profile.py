from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from app.services.user_service import UserService
from app.bot.keyboards.main_menu import MainMenuCallback, get_back_to_menu_keyboard
from app.bot.keyboards.profile import get_profile_keyboard, ProfileCallback, get_deposit_keyboard
from app.bot.utils.messages import get_profile_text, get_balance_details_text, get_deposit_text

router = Router()

@router.callback_query(MainMenuCallback.filter(F.action == "profile"))
@router.message(Command("profile"))
async def show_profile(
    update: CallbackQuery | Message,
    user: User
):
    """Показать профиль пользователя"""
    profile_text = get_profile_text(user)
    keyboard = get_profile_keyboard(user)
    
    if isinstance(update, CallbackQuery):
        await update.message.edit_text(profile_text, reply_markup=keyboard)
        await update.answer()
    else:
        await update.answer(profile_text, reply_markup=keyboard)

@router.callback_query(ProfileCallback.filter(F.action == "balance"))
async def show_balance_info(callback: CallbackQuery, user: User):
    """Показать подробную информацию о балансе"""
    balance_text = get_balance_details_text(user)
    
    await callback.message.edit_text(
        balance_text,
        reply_markup=get_back_to_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(ProfileCallback.filter(F.action == "stats"))
async def show_detailed_stats(callback: CallbackQuery, user: User, user_service: UserService):
    """Показать детальную статистику"""
    stats = await user_service.get_user_stats(user.telegram_id)
    
    stats_text = f"""📊 <b>ДЕТАЛЬНАЯ СТАТИСТИКА</b>

👤 <b>ПРОФИЛЬ:</b>
├ ID: <code>{user.telegram_id}</code>
├ Username: @{user.username or 'не указан'}
├ Уровень: {user.get_level_config()['name']}
└ Регистрация: {user.created_at.strftime('%d.%m.%Y')}

💼 <b>АКТИВНОСТЬ:</b>
├ Выполнено заданий: {user.tasks_completed}
├ Создано заданий: {user.tasks_created}
├ Рефералов: {user.total_referrals}
└ Premium рефералов: {user.premium_referrals}

💰 <b>ДОХОДЫ:</b>
├ От заданий: {user.total_earned:,.0f} GRAM
├ От рефералов: {user.referral_earnings:,.0f} GRAM
└ Всего заработано: {user.total_earned + user.referral_earnings:,.0f} GRAM

📊 <b>ТРАНЗАКЦИИ:</b>
├ Всего операций: {stats['total_transactions']}
├ Общий доход: {stats['total_income']:,.0f} GRAM
└ Общие расходы: {stats['total_spending']:,.0f} GRAM

⚙️ <b>НАСТРОЙКИ УРОВНЯ:</b>
├ Комиссия: {user.get_level_config()['commission_rate']*100:.0f}%
├ Множитель наград: x{user.get_level_config()['task_multiplier']}
└ Реферальный бонус: {user.get_level_config()['referral_bonus']:,.0f} GRAM"""
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=get_back_to_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(ProfileCallback.filter(F.action == "deposit"))
async def show_deposit_menu(callback: CallbackQuery):
    """Показать меню пополнения"""
    text = """💳 <b>ПОПОЛНЕНИЕ БАЛАНСА</b>

Выберите пакет Telegram Stars для пополнения:

⭐ <b>Преимущества Stars:</b>
• Мгновенное зачисление
• Безопасные платежи через Telegram
• Бонусы за крупные покупки
• Поддержка всех способов оплаты

💡 <i>Чем больше пакет, тем выгоднее курс!</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_deposit_keyboard()
    )
    await callback.answer()

@router.callback_query(ProfileCallback.filter(F.action == "my_tasks"))
async def show_my_tasks(callback: CallbackQuery, user: User, task_service):
    """Показать мои задания"""
    from app.services.task_service import TaskService
    
    task_service = TaskService()
    tasks = await task_service.get_user_tasks(user.telegram_id, limit=10)
    
    if not tasks:
        text = """🎯 <b>МОИ ЗАДАНИЯ</b>

📭 У вас пока нет созданных заданий.

Создайте свое первое задание:
• Выберите тип продвижения
• Настройте параметры
• Получайте результат!"""
    else:
        from app.bot.utils.messages import get_my_tasks_text
        text = get_my_tasks_text(tasks)
    
    from app.bot.keyboards.advertise import get_my_tasks_keyboard
    
    await callback.message.edit_text(
        text,
        reply_markup=get_my_tasks_keyboard(tasks)
    )
    await callback.answer()

@router.callback_query(ProfileCallback.filter(F.action == "executed_tasks"))
async def show_executed_tasks(callback: CallbackQuery, user: User):
    """Показать выполненные задания"""
    from app.services.task_service import TaskService
    
    task_service = TaskService()
    executions = await task_service.get_user_executions(user.telegram_id, limit=10)
    
    if not executions:
        text = """💼 <b>ВЫПОЛНЕННЫЕ ЗАДАНИЯ</b>

📭 Вы пока не выполняли задания.

Начните зарабатывать:
• Перейдите в раздел "💰 Заработать"
• Выберите подходящее задание
• Получите награду!"""
    else:
        text = f"""💼 <b>ВЫПОЛНЕННЫЕ ЗАДАНИЯ</b>

📊 Всего выполнений: {len(executions)}
💰 Заработано: {sum(ex.reward_amount for ex in executions):,.0f} GRAM

🕐 <b>ПОСЛЕДНИЕ ВЫПОЛНЕНИЯ:</b>"""
        
        for execution in executions[:5]:
            status_emoji = "✅" if execution.status.value == "completed" else "⏳"
            date = execution.created_at.strftime('%d.%m %H:%M')
            text += f"\n{status_emoji} {execution.reward_amount:,.0f} GRAM | {date}"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(ProfileCallback.filter(F.action == "referrals"))
async def show_referrals(callback: CallbackQuery, user: User, user_service: UserService):
    """Показать рефералов"""
    referrals = await user_service.get_user_referrals(user.telegram_id, limit=10)
    
    if not referrals:
        text = f"""👥 <b>МОИ РЕФЕРАЛЫ</b>

📭 У вас пока нет рефералов.

🔗 Ваша реферальная ссылка:
<code>https://t.me/{settings.BOT_USERNAME}?start={user.telegram_id}</code>

💰 За каждого реферала: {user.get_level_config()['referral_bonus']:,.0f} GRAM"""
    else:
        text = f"""👥 <b>МОИ РЕФЕРАЛЫ</b>

📊 Всего: {user.total_referrals} | Premium: {user.premium_referrals}
💰 Заработано: {user.referral_earnings:,.0f} GRAM

👤 <b>ПОСЛЕДНИЕ РЕФЕРАЛЫ:</b>"""
        
        for referral in referrals[:5]:
            level_emoji = {"bronze": "🥉", "silver": "🥈", "gold": "🥇", "premium": "💎"}.get(referral.level, "❓")
            date = referral.created_at.strftime('%d.%m.%Y')
            username = referral.username or f"ID{referral.telegram_id}"
            text += f"\n{level_emoji} @{username} | {date}"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(ProfileCallback.filter(F.action == "transactions"))
async def show_transactions(callback: CallbackQuery, user: User, transaction_service):
    """Показать историю транзакций"""
    from app.services.transaction_service import TransactionService
    
    transaction_service = TransactionService()
    transactions = await transaction_service.get_user_transactions(user.telegram_id, limit=10)
    
    if not transactions:
        text = """📜 <b>ИСТОРИЯ ТРАНЗАКЦИЙ</b>

📭 История транзакций пуста.

Транзакции появятся после:
• Выполнения заданий
• Пополнения баланса
• Создания заданий"""
    else:
        text = f"""📜 <b>ИСТОРИЯ ТРАНЗАКЦИЙ</b>

📊 Всего операций: {len(transactions)}

🕐 <b>ПОСЛЕДНИЕ ТРАНЗАКЦИИ:</b>"""
        
        for tx in transactions[:8]:
            amount_text = f"+{tx.amount:,.0f}" if tx.amount > 0 else f"{tx.amount:,.0f}"
            date = tx.created_at.strftime('%d.%m %H:%M')
            
            # Иконки типов транзакций
            type_icons = {
                "task_reward": "🎯",
                "referral_bonus": "👥",
                "deposit_stars": "⭐",
                "task_creation": "📢"
            }
            icon = type_icons.get(tx.type.value, "💰")
            
            text += f"\n{icon} {amount_text} GRAM | {date}"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_menu_keyboard()
    )
    await callback.answer()