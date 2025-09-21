from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from app.database.models.user import User
from app.services.user_service import UserService
from app.bot.keyboards.referral import ReferralCallback, get_referral_keyboard, get_referral_link_keyboard
from app.bot.keyboards.main_menu import get_back_to_menu_keyboard
from app.bot.utils.messages import get_referral_text
from app.config.settings import settings

router = Router()

@router.message(Command("referral"))
async def cmd_referral(message: Message, user: User):
    """Команда /referral"""
    text = get_referral_text(user)
    
    await message.answer(
        text,
        reply_markup=get_referral_keyboard()
    )

@router.callback_query(ReferralCallback.filter(F.action == "menu"))
async def show_referral_menu(callback: CallbackQuery, user: User):
    """Показать меню реферальной системы"""
    text = get_referral_text(user)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_referral_keyboard()
    )
    await callback.answer()

@router.callback_query(ReferralCallback.filter(F.action == "link"))
async def show_referral_link(callback: CallbackQuery, user: User):
    """Показать реферальную ссылку"""
    referral_link = f"https://t.me/{settings.BOT_USERNAME}?start={user.telegram_id}"
    
    text = f"""🔗 <b>ВАША РЕФЕРАЛЬНАЯ ССЫЛКА</b>

<code>{referral_link}</code>

💰 <b>ЗА КАЖДОГО РЕФЕРАЛА:</b>
├ Регистрация: {user.get_level_config()['referral_bonus']:,.0f} GRAM
├ От активности: 5% от заработка
└ От пополнений: 10% от депозитов

📤 <b>КАК ПРИГЛАСИТЬ:</b>
• Отправьте ссылку друзьям
• Поделитесь в социальных сетях  
• Добавьте в описание канала
• Используйте кнопку "Поделиться"

🎯 <b>СОВЕТЫ:</b>
• Объясните преимущества бота
• Покажите, как легко зарабатывать
• Помогите с первыми заданиями"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_referral_link_keyboard(user.telegram_id)
    )
    await callback.answer()

@router.callback_query(ReferralCallback.filter(F.action == "list"))
async def show_referral_list(
    callback: CallbackQuery, 
    callback_data: ReferralCallback,
    user: User, 
    user_service: UserService
):
    """Показать список рефералов"""
    page = callback_data.page
    limit = 10
    offset = (page - 1) * limit
    
    # Получаем рефералов
    referrals = await user_service.get_user_referrals(
        user.telegram_id, 
        limit=limit + 1
    )
    
    has_next = len(referrals) > limit
    if has_next:
        referrals = referrals[:limit]
    
    if not referrals:
        text = f"""👥 <b>МОИ РЕФЕРАЛЫ</b>

📭 У вас пока нет рефералов.

🔗 Ваша реферальная ссылка:
<code>https://t.me/{settings.BOT_USERNAME}?start={user.telegram_id}</code>

💰 За каждого реферала: {user.get_level_config()['referral_bonus']:,.0f} GRAM

💡 <b>Как привлечь рефералов:</b>
• Поделитесь ссылкой с друзьями
• Расскажите о возможностях бота
• Опубликуйте в социальных сетях"""
    else:
        text = f"""👥 <b>МОИ РЕФЕРАЛЫ</b>

📊 Всего: {user.total_referrals} | Premium: {user.premium_referrals}
💰 Заработано: {user.referral_earnings:,.0f} GRAM

👤 <b>СПИСОК РЕФЕРАЛОВ</b> (стр. {page}):"""
        
        for i, referral in enumerate(referrals, 1):
            level_emoji = {
                "bronze": "🥉", "silver": "🥈", 
                "gold": "🥇", "premium": "💎"
            }.get(referral.level, "❓")
            
            date = referral.created_at.strftime('%d.%m.%Y')
            username = referral.username or f"ID{referral.telegram_id}"
            
            # Статистика реферала
            tasks_done = referral.tasks_completed
            balance = referral.balance
            
            text += f"\n\n{i}. {level_emoji} @{username}"
            text += f"\n├ Регистрация: {date}"
            text += f"\n├ Заданий: {tasks_done}"
            text += f"\n└ Баланс: {balance:,.0f} GRAM"
    
    # Навигационные кнопки
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=ReferralCallback(action="list", page=page-1).pack()
            )
        )
    
    if has_next:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Вперед",
                callback_data=ReferralCallback(action="list", page=page+1).pack()
            )
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(
        InlineKeyboardButton(
            text="🔄 Обновить",
            callback_data=ReferralCallback(action="list", page=page).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=ReferralCallback(action="menu").pack()
        )
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(ReferralCallback.filter(F.action == "earnings"))
async def show_referral_earnings(callback: CallbackQuery, user: User, user_service: UserService):
    """Показать доходы с рефералов"""
    # Получаем детальную статистику
    stats = await user_service.get_user_stats(user.telegram_id)
    
    # Рассчитываем среднюю доходность
    avg_earning = 0
    if user.total_referrals > 0:
        avg_earning = user.referral_earnings / user.total_referrals
    
    # Потенциальный доход в месяц (примерная оценка)
    potential_monthly = user.total_referrals * 100  # Условно 100 GRAM в месяц с реферала
    
    text = f"""💰 <b>ДОХОДЫ С РЕФЕРАЛОВ</b>

📊 <b>ОБЩАЯ СТАТИСТИКА:</b>
├ Всего рефералов: {user.total_referrals}
├ Premium рефералов: {user.premium_referrals}
├ Заработано всего: {user.referral_earnings:,.0f} GRAM
└ Средний доход с реферала: {avg_earning:,.0f} GRAM

💵 <b>ИСТОЧНИКИ ДОХОДА:</b>
├ За регистрации: {user.get_level_config()['referral_bonus']:,.0f} GRAM за реферала
├ От заданий: 5% от заработка рефералов
├ От пополнений: 10% от депозитов рефералов
└ Бонусы: дополнительные награды

📈 <b>ПОТЕНЦИАЛ:</b>
├ Ориентировочный доход в месяц: ~{potential_monthly:,.0f} GRAM
├ При привлечении 10 активных: ~{potential_monthly * 10:,.0f} GRAM
└ При привлечении 100 активных: ~{potential_monthly * 100:,.0f} GRAM

🎯 <b>КАК УВЕЛИЧИТЬ ДОХОДЫ:</b>
• Привлекайте больше рефералов
• Помогайте им разобраться с ботом
• Мотивируйте на активное участие
• Поощряйте пополнение баланса"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(ReferralCallback.filter(F.action == "stats"))
async def show_referral_stats(callback: CallbackQuery, user: User, user_service: UserService):
    """Показать детальную статистику рефералов"""
    referrals = await user_service.get_user_referrals(user.telegram_id, limit=1000)
    
    # Анализируем рефералов
    stats_by_level = {"bronze": 0, "silver": 0, "gold": 0, "premium": 0}
    active_referrals = 0
    total_referral_balance = 0
    total_referral_tasks = 0
    
    for ref in referrals:
        stats_by_level[ref.level] += 1
        total_referral_balance += ref.balance
        total_referral_tasks += ref.tasks_completed
        
        # Считаем активными тех, кто был онлайн в последние 7 дней
        if ref.last_activity:
            from datetime import datetime, timedelta
            week_ago = datetime.utcnow() - timedelta(days=7)
            if ref.last_activity > week_ago:
                active_referrals += 1
    
    # Конверсия в Premium
    premium_conversion = 0
    if user.total_referrals > 0:
        premium_conversion = (user.premium_referrals / user.total_referrals) * 100
    
    text = f"""📊 <b>СТАТИСТИКА РЕФЕРАЛОВ</b>

👥 <b>РАСПРЕДЕЛЕНИЕ ПО УРОВНЯМ:</b>
├ 🥉 Bronze: {stats_by_level['bronze']}
├ 🥈 Silver: {stats_by_level['silver']}
├ 🥇 Gold: {stats_by_level['gold']}
└ 💎 Premium: {stats_by_level['premium']}

📈 <b>АКТИВНОСТЬ:</b>
├ Всего рефералов: {user.total_referrals}
├ Активных (неделя): {active_referrals}
├ Коэффициент активности: {(active_referrals/user.total_referrals*100 if user.total_referrals > 0 else 0):.1f}%
└ Конверсия в Premium: {premium_conversion:.1f}%

💰 <b>ЭКОНОМИЧЕСКИЕ ПОКАЗАТЕЛИ:</b>
├ Общий баланс рефералов: {total_referral_balance:,.0f} GRAM
├ Выполнено заданий: {total_referral_tasks}
├ Ваши доходы: {user.referral_earnings:,.0f} GRAM
└ ROI реферальной системы: высокий

🎯 <b>РЕКОМЕНДАЦИИ:</b>"""
    
    if user.total_referrals < 10:
        text += "\n• Привлекайте больше рефералов"
    if premium_conversion < 10:
        text += "\n• Мотивируйте рефералов к Premium"
    if active_referrals < user.total_referrals * 0.5:
        text += "\n• Повышайте активность рефералов"
    
    text += "\n• Регулярно общайтесь с рефералами"
    text += "\n• Помогайте с первыми заданиями"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_menu_keyboard()
    )
    await callback.answer()

