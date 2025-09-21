from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from decimal import Decimal

from app.database.models.user import User
from app.database.models.check import CheckType
from app.services.check_service import CheckService
from app.bot.keyboards.checks import (
    CheckCallback, get_checks_menu_keyboard, get_check_type_keyboard,
    get_my_checks_keyboard, get_check_management_keyboard,
    get_check_activation_keyboard, get_activated_checks_keyboard,
    get_cancel_keyboard
)
from app.bot.keyboards.main_menu import get_main_menu_keyboard
from app.bot.states.check_creation import CheckCreationStates
from app.bot.utils.messages import get_error_message, get_success_message

router = Router()

@router.message(Command("checks"))
async def cmd_checks(message: Message, user: User):
    """Команда /checks"""
    text = """💳 <b>СИСТЕМА ЧЕКОВ</b>

Отправляйте GRAM монеты через специальные чеки прямо в сообщениях Telegram.

💰 Баланс: {user.balance:,.0f} GRAM

🎯 <b>ВОЗМОЖНОСТИ ЧЕКОВ:</b>
• Отправка в любой чат/канал
• Добавление комментариев и картинок
• Установка пароля для защиты
• Условие подписки для получения
• Уведомления о создании и активации"""
    
    await message.answer(
        text,
        reply_markup=get_checks_menu_keyboard()
    )

@router.callback_query(CheckCallback.filter(F.action == "cancel"))
async def cancel_check(
    callback: CallbackQuery,
    callback_data: CheckCallback,
    user: User,
    check_service: CheckService
):
    """Отменить чек"""
    check_id = callback_data.check_id
    
    success = await check_service.cancel_check(check_id, user.telegram_id)
    
    if success:
        text = """✅ <b>ЧЕК ОТМЕНЕН</b>

Чек успешно отменен.
💰 Неиспользованные средства возвращены на баланс."""
        
        await callback.message.edit_text(
            text,
            reply_markup=get_main_menu_keyboard(user)
        )
        await callback.answer("✅ Чек отменен")
    else:
        await callback.answer("❌ Не удалось отменить чек", show_alert=True)

@router.callback_query(CheckCallback.filter(F.action == "analytics"))
async def show_check_analytics(
    callback: CallbackQuery,
    callback_data: CheckCallback,
    check_service: CheckService
):
    """Показать аналитику чека"""
    analytics = await check_service.get_check_analytics(callback_data.check_id)
    
    if not analytics:
        await callback.answer("❌ Не удалось загрузить аналитику", show_alert=True)
        return
    
    check = analytics['check']
    
    text = f"""📊 <b>АНАЛИТИКА ЧЕКА</b>

💳 <b>Чек:</b> #{check.check_code}
📅 <b>Создан:</b> {check.created_at.strftime('%d.%m.%Y %H:%M')}

📈 <b>АКТИВНОСТИ:</b>
├ Всего активаций: {analytics['total_activations']}
├ Прогресс: {analytics['completion_percentage']:.1f}%
├ Распределено: {analytics['total_distributed']:,.0f} GRAM
└ Остается: {check.remaining_amount:,.0f} GRAM

⏱️ <b>АКТИВАЦИИ ПО ВРЕМЕНИ:</b>"""
    
    # Добавляем последние активации
    if analytics['activations']:
        text += "\n\n🕐 <b>ПОСЛЕДНИЕ АКТИВАЦИИ:</b>"
        for activation in analytics['activations'][-5:]:  # Последние 5
            time_str = activation.activated_at.strftime('%d.%m %H:%M')
            text += f"\n├ {activation.amount_received:,.0f} GRAM | {time_str}"
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к чеку",
            callback_data=CheckCallback(action="manage", check_id=check.id).pack()
        )
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(CheckCallback.filter(F.action == "activated"))
async def show_activated_checks(
    callback: CallbackQuery,
    callback_data: CheckCallback,
    user: User,
    check_service: CheckService
):
    """Показать активированные чеки"""
    page = callback_data.page
    limit = 10
    offset = (page - 1) * limit
    
    activations = await check_service.get_user_activations(
        user.telegram_id,
        limit=limit + 1,
        offset=offset
    )
    
    has_next = len(activations) > limit
    if has_next:
        activations = activations[:limit]
    
    if not activations:
        text = """💰 <b>АКТИВИРОВАННЫЕ ЧЕКИ</b>

📭 Вы пока не активировали ни одного чека.

Найдите чеки:
• В сообщениях от друзей
• В каналах и группах
• Используйте команду /check КОД"""
    else:
        total_received = sum(a.amount_received for a in activations)
        
        text = f"""💰 <b>АКТИВИРОВАННЫЕ ЧЕКИ</b>

📊 Всего активаций: {len(activations)}
💰 Получено: {total_received:,.0f} GRAM
📄 Страница: {page}

🕐 <b>ПОСЛЕДНИЕ АКТИВАЦИИ:</b>"""
        
        for activation in activations:
            time_str = activation.activated_at.strftime('%d.%m %H:%M')
            text += f"\n├ {activation.amount_received:,.0f} GRAM | {time_str}"
    
    keyboard = get_activated_checks_keyboard(activations, page, has_next)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(CheckCallback.filter(F.action == "copy_code"))
async def copy_check_code(
    callback: CallbackQuery,
    callback_data: CheckCallback,
    check_service: CheckService
):
    """Скопировать код чека"""
    check_id = callback_data.check_id
    
    analytics = await check_service.get_check_analytics(check_id)
    if not analytics:
        await callback.answer("❌ Чек не найден", show_alert=True)
        return
    
    check = analytics['check']
    
    text = f"""📋 <b>КОД ЧЕКА</b>

Код для активации:
<code>{check.check_code}</code>

💡 <b>Как поделиться:</b>
• Скопируйте код выше
• Отправьте друзьям в любом чате
• Они активируют: /check {check.check_code}"""
    
    if check.password:
        text += f"\n\n🔒 Пароль: <code>{check.password}</code>"
        text += f"\nДля активации: <code>/check {check.check_code} {check.password}</code>"
    
    await callback.answer("📋 Код скопирован!", show_alert=True)
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к чеку",
            callback_data=CheckCallback(action="manage", check_id=check.id).pack()
        )
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())

# Обработчик текстовых сообщений для активации чеков
@router.message(F.text.regexp(r'^[A-Z0-9]{8}Callback.filter(F.action == "menu"))
async def show_checks_menu(callback: CallbackQuery, user: User):
    """Показать меню чеков"""
    text = f"""💳 <b>СИСТЕМА ЧЕКОВ</b>

Отправляйте GRAM монеты через специальные чеки прямо в сообщениях Telegram.

💰 Баланс: {user.balance:,.0f} GRAM

🎯 <b>ВОЗМОЖНОСТИ ЧЕКОВ:</b>
• Отправка в любой чат/канал
• Добавление комментариев и картинок
• Установка пароля для защиты
• Условие подписки для получения
• Уведомления о создании и активации"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_checks_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(CheckCallback.filter(F.action == "create_menu"))
async def show_create_menu(callback: CallbackQuery):
    """Показать меню создания чека"""
    text = """➕ <b>СОЗДАНИЕ ЧЕКА</b>

Выберите тип чека:

👤 <b>Персональный чек</b>
• Для одного получателя
• Можно указать конкретного пользователя
• Максимальная безопасность

👥 <b>Мульти-чек</b>
• Для нескольких получателей
• Можно установить лимит активаций
• Отлично для раздач

🎁 <b>Розыгрыш</b>
• Случайное распределение
• Разные суммы для каждого
• Интерактивные функции"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_check_type_keyboard()
    )
    await callback.answer()

@router.callback_query(CheckCallback.filter(F.action == "create"))
async def start_check_creation(
    callback: CallbackQuery,
    callback_data: CheckCallback,
    state: FSMContext,
    user: User
):
    """Начать создание чека"""
    check_type = callback_data.check_type
    
    # Проверяем баланс
    if user.available_balance < 10:  # Минимум 10 GRAM
        await callback.answer("❌ Недостаточно средств (минимум 10 GRAM)", show_alert=True)
        return
    
    # Устанавливаем состояние
    await state.set_state(CheckCreationStates.entering_amount)
    await state.update_data(check_type=check_type)
    
    # Названия типов
    type_names = {
        "personal": "👤 Персональный чек",
        "multi": "👥 Мульти-чек",
        "giveaway": "🎁 Розыгрыш"
    }
    
    type_name = type_names.get(check_type, "Чек")
    
    text = f"""💳 <b>СОЗДАНИЕ ЧЕКА</b>

🎯 <b>Тип:</b> {type_name}

Введите общую сумму чека в GRAM:

💡 <b>Рекомендации:</b>
• Минимум: 10 GRAM
• Доступно: {user.available_balance:,.0f} GRAM
• Учитывайте комиссию сервиса

❌ <i>Для отмены отправьте /cancel</i>"""
    
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard())
    await callback.answer()

@router.message(CheckCreationStates.entering_amount)
async def process_check_amount(message: Message, state: FSMContext, user: User):
    """Обработка суммы чека"""
    try:
        amount = Decimal(message.text.strip())
    except (ValueError, TypeError):
        await message.answer("❌ Введите корректную сумму\n\nПопробуйте еще раз:")
        return
    
    if amount < 10:
        await message.answer("❌ Минимальная сумма: 10 GRAM\n\nПопробуйте еще раз:")
        return
    
    if amount > user.available_balance:
        await message.answer(f"❌ Недостаточно средств\n\nДоступно: {user.available_balance:,.0f} GRAM\n\nПопробуйте еще раз:")
        return
    
    # Сохраняем сумму
    await state.update_data(amount=amount)
    await state.set_state(CheckCreationStates.entering_activations)
    
    data = await state.get_data()
    check_type = data["check_type"]
    
    if check_type == "personal":
        # Для персонального чека сразу переходим к настройкам
        await state.update_data(max_activations=1)
        await state.set_state(CheckCreationStates.entering_comment)
        
        text = f"""💳 <b>СОЗДАНИЕ ПЕРСОНАЛЬНОГО ЧЕКА</b>

✅ <b>Сумма:</b> {amount:,.0f} GRAM
✅ <b>Получателей:</b> 1

Введите комментарий к чеку (необязательно):

💡 <b>Примеры:</b>
• "Спасибо за помощь!"
• "Бонус за активность"
• "Подарок от друга"

⏭️ <i>Для пропуска отправьте "-"</i>
❌ <i>Для отмены отправьте /cancel</i>"""
        
        await message.answer(text)
    else:
        text = f"""💳 <b>СОЗДАНИЕ МУЛЬТИ-ЧЕКА</b>

✅ <b>Общая сумма:</b> {amount:,.0f} GRAM

Введите количество активаций (получателей):

💡 <b>Рекомендации:</b>
• Минимум: 2 активации
• Максимум: 1000 активаций
• Каждый получит: {amount:,.0f} ÷ количество

❌ <i>Для отмены отправьте /cancel</i>"""
        
        await message.answer(text)

@router.message(CheckCreationStates.entering_activations)
async def process_check_activations(message: Message, state: FSMContext):
    """Обработка количества активаций"""
    try:
        activations = int(message.text.strip())
    except (ValueError, TypeError):
        await message.answer("❌ Введите корректное число\n\nПопробуйте еще раз:")
        return
    
    if activations < 2:
        await message.answer("❌ Минимум активаций: 2\n\nПопробуйте еще раз:")
        return
    
    if activations > 1000:
        await message.answer("❌ Максимум активаций: 1000\n\nПопробуйте еще раз:")
        return
    
    data = await state.get_data()
    amount = data["amount"]
    amount_per_activation = amount / activations
    
    if amount_per_activation < 1:
        await message.answer(f"❌ Слишком много активаций\n\nПри {activations} активациях каждый получит {amount_per_activation:.2f} GRAM\nМинимум на активацию: 1 GRAM\n\nПопробуйте еще раз:")
        return
    
    # Сохраняем количество
    await state.update_data(max_activations=activations)
    await state.set_state(CheckCreationStates.entering_comment)
    
    text = f"""💳 <b>СОЗДАНИЕ МУЛЬТИ-ЧЕКА</b>

✅ <b>Общая сумма:</b> {amount:,.0f} GRAM
✅ <b>Активаций:</b> {activations}
✅ <b>На активацию:</b> {amount_per_activation:,.0f} GRAM

Введите комментарий к чеку (необязательно):

💡 <b>Примеры:</b>
• "Раздача для подписчиков!"
• "Бонус за активность в канале"
• "Новогодний подарок"

⏭️ <i>Для пропуска отправьте "-"</i>
❌ <i>Для отмены отправьте /cancel</i>"""
    
    await message.answer(text)

@router.message(CheckCreationStates.entering_comment)
async def process_check_comment(message: Message, state: FSMContext):
    """Обработка комментария чека"""
    comment = message.text.strip()
    
    if comment == "-":
        comment = None
    elif len(comment) > 200:
        await message.answer("❌ Комментарий слишком длинный (максимум 200 символов)\n\nПопробуйте еще раз:")
        return
    
    # Сохраняем комментарий
    await state.update_data(description=comment)
    await state.set_state(CheckCreationStates.entering_password)
    
    text = """🔒 <b>ПАРОЛЬ ДЛЯ ЧЕКА</b>

Установите пароль для защиты чека (необязательно):

💡 <b>Зачем нужен пароль:</b>
• Дополнительная защита
• Ограничение доступа
• Раздача только определенным людям

⏭️ <i>Для пропуска отправьте "-"</i>
❌ <i>Для отмены отправьте /cancel</i>"""
    
    await message.answer(text)

@router.message(CheckCreationStates.entering_password)
async def process_check_password(message: Message, state: FSMContext, user: User, check_service: CheckService):
    """Обработка пароля и создание чека"""
    password = message.text.strip()
    
    if password == "-":
        password = None
    elif len(password) > 50:
        await message.answer("❌ Пароль слишком длинный (максимум 50 символов)\n\nПопробуйте еще раз:")
        return
    
    # Получаем все данные
    data = await state.get_data()
    
    check_type = CheckType(data["check_type"])
    amount = data["amount"]
    max_activations = data["max_activations"]
    description = data.get("description")
    
    # Создаем чек
    check = await check_service.create_check(
        creator_id=user.telegram_id,
        check_type=check_type,
        total_amount=amount,
        max_activations=max_activations,
        description=description,
        password=password,
        expires_in_hours=24 * 7  # 7 дней
    )
    
    if check:
        amount_per_activation = amount / max_activations
        
        text = f"""✅ <b>ЧЕК СОЗДАН!</b>

💳 <b>Код чека:</b> <code>{check.check_code}</code>
💰 <b>Сумма:</b> {amount:,.0f} GRAM
👥 <b>Активаций:</b> {max_activations}
🎁 <b>На активацию:</b> {amount_per_activation:,.0f} GRAM

🔗 <b>Как поделиться:</b>
• Отправьте код другим пользователям
• Используйте кнопку "Поделиться" 
• Активация: <code>/check {check.check_code}</code>

⏰ <b>Срок действия:</b> 7 дней"""
        
        if password:
            text += f"\n🔒 <b>Пароль:</b> <code>{password}</code>"
        
        if description:
            text += f"\n💬 <b>Комментарий:</b> {description}"
        
        await message.answer(
            text,
            reply_markup=get_check_management_keyboard(check)
        )
        
        await state.clear()
    else:
        await message.answer("❌ Не удалось создать чек. Попробуйте позже.")
        await state.clear()

@router.callback_query(CheckCallback.filter(F.action == "my_checks"))
async def show_my_checks(
    callback: CallbackQuery,
    callback_data: CheckCallback,
    user: User,
    check_service: CheckService
):
    """Показать мои чеки"""
    page = callback_data.page
    limit = 10
    offset = (page - 1) * limit
    
    checks = await check_service.get_user_checks(
        user.telegram_id,
        limit=limit + 1,
        offset=offset
    )
    
    has_next = len(checks) > limit
    if has_next:
        checks = checks[:limit]
    
    if not checks:
        text = """📋 <b>МОИ ЧЕКИ</b>

📭 У вас пока нет созданных чеков.

Создайте свой первый чек:
• Выберите тип чека
• Настройте параметры
• Поделитесь с друзьями!"""
    else:
        text = f"""📋 <b>МОИ ЧЕКИ</b>

📊 Всего: {len(checks)} | Страница: {page}

Выберите чек для управления:"""
    
    keyboard = get_my_checks_keyboard(checks, page, has_next)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(CheckCallback.filter(F.action == "manage"))
async def manage_check(
    callback: CallbackQuery,
    callback_data: CheckCallback,
    check_service: CheckService
):
    """Управление чеком"""
    check_id = callback_data.check_id
    
    # Получаем аналитику чека
    analytics = await check_service.get_check_analytics(check_id)
    
    if not analytics:
        await callback.answer("❌ Чек не найден", show_alert=True)
        return
    
    check = analytics['check']
    
    # Статус чека
    status_icons = {
        "active": "🟢 Активный",
        "expired": "⏰ Истек",
        "completed": "✅ Завершен",
        "cancelled": "❌ Отменен"
    }
    
    status_text = status_icons.get(check.status, "❓ Неизвестно")
    
    text = f"""💳 <b>УПРАВЛЕНИЕ ЧЕКОМ</b>

🆔 <b>Код:</b> <code>{check.check_code}</code>
📊 <b>Статус:</b> {status_text}
💰 <b>Сумма:</b> {check.amount_per_activation:,.0f} GRAM за активацию

📈 <b>ПРОГРЕСС:</b>
├ Активировано: {check.current_activations}/{check.max_activations}
├ Процент: {analytics['completion_percentage']:.1f}%
└ Осталось: {check.remaining_activations}

💳 <b>ФИНАНСЫ:</b>
├ Общая сумма: {check.total_amount:,.0f} GRAM
├ Распределено: {analytics['total_distributed']:,.0f} GRAM
└ Остается: {check.remaining_amount:,.0f} GRAM

📅 <b>Создан:</b> {check.created_at.strftime('%d.%m.%Y %H:%M')}"""
    
    if check.expires_at:
        text += f"\n⏰ <b>Истекает:</b> {check.expires_at.strftime('%d.%m.%Y %H:%M')}"
    
    if check.description:
        text += f"\n💬 <b>Комментарий:</b> {check.description}"
    
    keyboard = get_check_management_keyboard(check)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(CheckCallback.filter(F.action == "activate"))
async def show_activate_form(callback: CallbackQuery):
    """Показать форму активации чека"""
    text = """🎫 <b>АКТИВАЦИЯ ЧЕКА</b>

Отправьте код чека для активации:

💡 <b>Как активировать:</b>
• Введите 8-значный код чека
• Или используйте команду: <code>/check КОД</code>
• Если чек с паролем, введите: <code>КОД пароль</code>

🔍 <b>Пример:</b>
• <code>AB12CD34</code>
• <code>AB12CD34 mypassword</code>

❌ <i>Для отмены отправьте /cancel</i>"""
    
    await callback.message.edit_text(text, reply_markup=get_check_activation_keyboard())
    await callback.answer()

@router.message(Command("check"))
async def cmd_activate_check(message: Message, user: User, check_service: CheckService):
    """Команда /check для активации"""
    args = message.text.split()
    
    if len(args) < 2:
        await message.answer("❌ Введите код чека: /check КОД")
        return
    
    check_code = args[1].upper()
    password = args[2] if len(args) > 2 else None
    
    # Активируем чек
    success, message_text, amount = await check_service.activate_check(
        check_code, user.telegram_id, password
    )
    
    if success:
        text = f"""🎉 <b>ЧЕК АКТИВИРОВАН!</b>

💰 Получено: <b>{amount:,.0f} GRAM</b>
🆔 Код: <code>{check_code}</code>

💳 Средства зачислены на ваш баланс!"""
        
        await message.answer(text, reply_markup=get_main_menu_keyboard(user))
    else:
        await message.answer(f"{message_text}")

@router.callback_query(Check))
async def activate_check_by_text(message: Message, user: User, check_service: CheckService):
    """Активация чека по тексту (код из 8 символов)"""
    check_code = message.text.upper()
    
    success, message_text, amount = await check_service.activate_check(
        check_code, user.telegram_id
    )
    
    if success:
        text = f"""🎉 <b>ЧЕК АКТИВИРОВАН!</b>

💰 Получено: <b>{amount:,.0f} GRAM</b>
🆔 Код: <code>{check_code}</code>

💳 Средства зачислены на ваш баланс!"""
        
        await message.answer(text, reply_markup=get_main_menu_keyboard(user))
    else:
        await message.answer(f"{message_text}")

# Обработчик для кода с паролем
@router.message(F.text.regexp(r'^[A-Z0-9]{8}\s+\S+Callback.filter(F.action == "menu"))
async def show_checks_menu(callback: CallbackQuery, user: User):
    """Показать меню чеков"""
    text = f"""💳 <b>СИСТЕМА ЧЕКОВ</b>

Отправляйте GRAM монеты через специальные чеки прямо в сообщениях Telegram.

💰 Баланс: {user.balance:,.0f} GRAM

🎯 <b>ВОЗМОЖНОСТИ ЧЕКОВ:</b>
• Отправка в любой чат/канал
• Добавление комментариев и картинок
• Установка пароля для защиты
• Условие подписки для получения
• Уведомления о создании и активации"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_checks_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(CheckCallback.filter(F.action == "create_menu"))
async def show_create_menu(callback: CallbackQuery):
    """Показать меню создания чека"""
    text = """➕ <b>СОЗДАНИЕ ЧЕКА</b>

Выберите тип чека:

👤 <b>Персональный чек</b>
• Для одного получателя
• Можно указать конкретного пользователя
• Максимальная безопасность

👥 <b>Мульти-чек</b>
• Для нескольких получателей
• Можно установить лимит активаций
• Отлично для раздач

🎁 <b>Розыгрыш</b>
• Случайное распределение
• Разные суммы для каждого
• Интерактивные функции"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_check_type_keyboard()
    )
    await callback.answer()

@router.callback_query(CheckCallback.filter(F.action == "create"))
async def start_check_creation(
    callback: CallbackQuery,
    callback_data: CheckCallback,
    state: FSMContext,
    user: User
):
    """Начать создание чека"""
    check_type = callback_data.check_type
    
    # Проверяем баланс
    if user.available_balance < 10:  # Минимум 10 GRAM
        await callback.answer("❌ Недостаточно средств (минимум 10 GRAM)", show_alert=True)
        return
    
    # Устанавливаем состояние
    await state.set_state(CheckCreationStates.entering_amount)
    await state.update_data(check_type=check_type)
    
    # Названия типов
    type_names = {
        "personal": "👤 Персональный чек",
        "multi": "👥 Мульти-чек",
        "giveaway": "🎁 Розыгрыш"
    }
    
    type_name = type_names.get(check_type, "Чек")
    
    text = f"""💳 <b>СОЗДАНИЕ ЧЕКА</b>

🎯 <b>Тип:</b> {type_name}

Введите общую сумму чека в GRAM:

💡 <b>Рекомендации:</b>
• Минимум: 10 GRAM
• Доступно: {user.available_balance:,.0f} GRAM
• Учитывайте комиссию сервиса

❌ <i>Для отмены отправьте /cancel</i>"""
    
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard())
    await callback.answer()

@router.message(CheckCreationStates.entering_amount)
async def process_check_amount(message: Message, state: FSMContext, user: User):
    """Обработка суммы чека"""
    try:
        amount = Decimal(message.text.strip())
    except (ValueError, TypeError):
        await message.answer("❌ Введите корректную сумму\n\nПопробуйте еще раз:")
        return
    
    if amount < 10:
        await message.answer("❌ Минимальная сумма: 10 GRAM\n\nПопробуйте еще раз:")
        return
    
    if amount > user.available_balance:
        await message.answer(f"❌ Недостаточно средств\n\nДоступно: {user.available_balance:,.0f} GRAM\n\nПопробуйте еще раз:")
        return
    
    # Сохраняем сумму
    await state.update_data(amount=amount)
    await state.set_state(CheckCreationStates.entering_activations)
    
    data = await state.get_data()
    check_type = data["check_type"]
    
    if check_type == "personal":
        # Для персонального чека сразу переходим к настройкам
        await state.update_data(max_activations=1)
        await state.set_state(CheckCreationStates.entering_comment)
        
        text = f"""💳 <b>СОЗДАНИЕ ПЕРСОНАЛЬНОГО ЧЕКА</b>

✅ <b>Сумма:</b> {amount:,.0f} GRAM
✅ <b>Получателей:</b> 1

Введите комментарий к чеку (необязательно):

💡 <b>Примеры:</b>
• "Спасибо за помощь!"
• "Бонус за активность"
• "Подарок от друга"

⏭️ <i>Для пропуска отправьте "-"</i>
❌ <i>Для отмены отправьте /cancel</i>"""
        
        await message.answer(text)
    else:
        text = f"""💳 <b>СОЗДАНИЕ МУЛЬТИ-ЧЕКА</b>

✅ <b>Общая сумма:</b> {amount:,.0f} GRAM

Введите количество активаций (получателей):

💡 <b>Рекомендации:</b>
• Минимум: 2 активации
• Максимум: 1000 активаций
• Каждый получит: {amount:,.0f} ÷ количество

❌ <i>Для отмены отправьте /cancel</i>"""
        
        await message.answer(text)

@router.message(CheckCreationStates.entering_activations)
async def process_check_activations(message: Message, state: FSMContext):
    """Обработка количества активаций"""
    try:
        activations = int(message.text.strip())
    except (ValueError, TypeError):
        await message.answer("❌ Введите корректное число\n\nПопробуйте еще раз:")
        return
    
    if activations < 2:
        await message.answer("❌ Минимум активаций: 2\n\nПопробуйте еще раз:")
        return
    
    if activations > 1000:
        await message.answer("❌ Максимум активаций: 1000\n\nПопробуйте еще раз:")
        return
    
    data = await state.get_data()
    amount = data["amount"]
    amount_per_activation = amount / activations
    
    if amount_per_activation < 1:
        await message.answer(f"❌ Слишком много активаций\n\nПри {activations} активациях каждый получит {amount_per_activation:.2f} GRAM\nМинимум на активацию: 1 GRAM\n\nПопробуйте еще раз:")
        return
    
    # Сохраняем количество
    await state.update_data(max_activations=activations)
    await state.set_state(CheckCreationStates.entering_comment)
    
    text = f"""💳 <b>СОЗДАНИЕ МУЛЬТИ-ЧЕКА</b>

✅ <b>Общая сумма:</b> {amount:,.0f} GRAM
✅ <b>Активаций:</b> {activations}
✅ <b>На активацию:</b> {amount_per_activation:,.0f} GRAM

Введите комментарий к чеку (необязательно):

💡 <b>Примеры:</b>
• "Раздача для подписчиков!"
• "Бонус за активность в канале"
• "Новогодний подарок"

⏭️ <i>Для пропуска отправьте "-"</i>
❌ <i>Для отмены отправьте /cancel</i>"""
    
    await message.answer(text)

@router.message(CheckCreationStates.entering_comment)
async def process_check_comment(message: Message, state: FSMContext):
    """Обработка комментария чека"""
    comment = message.text.strip()
    
    if comment == "-":
        comment = None
    elif len(comment) > 200:
        await message.answer("❌ Комментарий слишком длинный (максимум 200 символов)\n\nПопробуйте еще раз:")
        return
    
    # Сохраняем комментарий
    await state.update_data(description=comment)
    await state.set_state(CheckCreationStates.entering_password)
    
    text = """🔒 <b>ПАРОЛЬ ДЛЯ ЧЕКА</b>

Установите пароль для защиты чека (необязательно):

💡 <b>Зачем нужен пароль:</b>
• Дополнительная защита
• Ограничение доступа
• Раздача только определенным людям

⏭️ <i>Для пропуска отправьте "-"</i>
❌ <i>Для отмены отправьте /cancel</i>"""
    
    await message.answer(text)

@router.message(CheckCreationStates.entering_password)
async def process_check_password(message: Message, state: FSMContext, user: User, check_service: CheckService):
    """Обработка пароля и создание чека"""
    password = message.text.strip()
    
    if password == "-":
        password = None
    elif len(password) > 50:
        await message.answer("❌ Пароль слишком длинный (максимум 50 символов)\n\nПопробуйте еще раз:")
        return
    
    # Получаем все данные
    data = await state.get_data()
    
    check_type = CheckType(data["check_type"])
    amount = data["amount"]
    max_activations = data["max_activations"]
    description = data.get("description")
    
    # Создаем чек
    check = await check_service.create_check(
        creator_id=user.telegram_id,
        check_type=check_type,
        total_amount=amount,
        max_activations=max_activations,
        description=description,
        password=password,
        expires_in_hours=24 * 7  # 7 дней
    )
    
    if check:
        amount_per_activation = amount / max_activations
        
        text = f"""✅ <b>ЧЕК СОЗДАН!</b>

💳 <b>Код чека:</b> <code>{check.check_code}</code>
💰 <b>Сумма:</b> {amount:,.0f} GRAM
👥 <b>Активаций:</b> {max_activations}
🎁 <b>На активацию:</b> {amount_per_activation:,.0f} GRAM

🔗 <b>Как поделиться:</b>
• Отправьте код другим пользователям
• Используйте кнопку "Поделиться" 
• Активация: <code>/check {check.check_code}</code>

⏰ <b>Срок действия:</b> 7 дней"""
        
        if password:
            text += f"\n🔒 <b>Пароль:</b> <code>{password}</code>"
        
        if description:
            text += f"\n💬 <b>Комментарий:</b> {description}"
        
        await message.answer(
            text,
            reply_markup=get_check_management_keyboard(check)
        )
        
        await state.clear()
    else:
        await message.answer("❌ Не удалось создать чек. Попробуйте позже.")
        await state.clear()

@router.callback_query(CheckCallback.filter(F.action == "my_checks"))
async def show_my_checks(
    callback: CallbackQuery,
    callback_data: CheckCallback,
    user: User,
    check_service: CheckService
):
    """Показать мои чеки"""
    page = callback_data.page
    limit = 10
    offset = (page - 1) * limit
    
    checks = await check_service.get_user_checks(
        user.telegram_id,
        limit=limit + 1,
        offset=offset
    )
    
    has_next = len(checks) > limit
    if has_next:
        checks = checks[:limit]
    
    if not checks:
        text = """📋 <b>МОИ ЧЕКИ</b>

📭 У вас пока нет созданных чеков.

Создайте свой первый чек:
• Выберите тип чека
• Настройте параметры
• Поделитесь с друзьями!"""
    else:
        text = f"""📋 <b>МОИ ЧЕКИ</b>

📊 Всего: {len(checks)} | Страница: {page}

Выберите чек для управления:"""
    
    keyboard = get_my_checks_keyboard(checks, page, has_next)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(CheckCallback.filter(F.action == "manage"))
async def manage_check(
    callback: CallbackQuery,
    callback_data: CheckCallback,
    check_service: CheckService
):
    """Управление чеком"""
    check_id = callback_data.check_id
    
    # Получаем аналитику чека
    analytics = await check_service.get_check_analytics(check_id)
    
    if not analytics:
        await callback.answer("❌ Чек не найден", show_alert=True)
        return
    
    check = analytics['check']
    
    # Статус чека
    status_icons = {
        "active": "🟢 Активный",
        "expired": "⏰ Истек",
        "completed": "✅ Завершен",
        "cancelled": "❌ Отменен"
    }
    
    status_text = status_icons.get(check.status, "❓ Неизвестно")
    
    text = f"""💳 <b>УПРАВЛЕНИЕ ЧЕКОМ</b>

🆔 <b>Код:</b> <code>{check.check_code}</code>
📊 <b>Статус:</b> {status_text}
💰 <b>Сумма:</b> {check.amount_per_activation:,.0f} GRAM за активацию

📈 <b>ПРОГРЕСС:</b>
├ Активировано: {check.current_activations}/{check.max_activations}
├ Процент: {analytics['completion_percentage']:.1f}%
└ Осталось: {check.remaining_activations}

💳 <b>ФИНАНСЫ:</b>
├ Общая сумма: {check.total_amount:,.0f} GRAM
├ Распределено: {analytics['total_distributed']:,.0f} GRAM
└ Остается: {check.remaining_amount:,.0f} GRAM

📅 <b>Создан:</b> {check.created_at.strftime('%d.%m.%Y %H:%M')}"""
    
    if check.expires_at:
        text += f"\n⏰ <b>Истекает:</b> {check.expires_at.strftime('%d.%m.%Y %H:%M')}"
    
    if check.description:
        text += f"\n💬 <b>Комментарий:</b> {check.description}"
    
    keyboard = get_check_management_keyboard(check)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(CheckCallback.filter(F.action == "activate"))
async def show_activate_form(callback: CallbackQuery):
    """Показать форму активации чека"""
    text = """🎫 <b>АКТИВАЦИЯ ЧЕКА</b>

Отправьте код чека для активации:

💡 <b>Как активировать:</b>
• Введите 8-значный код чека
• Или используйте команду: <code>/check КОД</code>
• Если чек с паролем, введите: <code>КОД пароль</code>

🔍 <b>Пример:</b>
• <code>AB12CD34</code>
• <code>AB12CD34 mypassword</code>

❌ <i>Для отмены отправьте /cancel</i>"""
    
    await callback.message.edit_text(text, reply_markup=get_check_activation_keyboard())
    await callback.answer()

@router.message(Command("check"))
async def cmd_activate_check(message: Message, user: User, check_service: CheckService):
    """Команда /check для активации"""
    args = message.text.split()
    
    if len(args) < 2:
        await message.answer("❌ Введите код чека: /check КОД")
        return
    
    check_code = args[1].upper()
    password = args[2] if len(args) > 2 else None
    
    # Активируем чек
    success, message_text, amount = await check_service.activate_check(
        check_code, user.telegram_id, password
    )
    
    if success:
        text = f"""🎉 <b>ЧЕК АКТИВИРОВАН!</b>

💰 Получено: <b>{amount:,.0f} GRAM</b>
🆔 Код: <code>{check_code}</code>

💳 Средства зачислены на ваш баланс!"""
        
        await message.answer(text, reply_markup=get_main_menu_keyboard(user))
    else:
        await message.answer(f"{message_text}")

@router.callback_query(Check))
async def activate_check_with_password(message: Message, user: User, check_service: CheckService):
    """Активация чека с паролем"""
    parts = message.text.split()
    check_code = parts[0].upper()
    password = parts[1]
    
    success, message_text, amount = await check_service.activate_check(
        check_code, user.telegram_id, password
    )
    
    if success:
        text = f"""🎉 <b>ЧЕК АКТИВИРОВАН!</b>

💰 Получено: <b>{amount:,.0f} GRAM</b>
🆔 Код: <code>{check_code}</code>

💳 Средства зачислены на ваш баланс!"""
        
        await message.answer(text, reply_markup=get_main_menu_keyboard(user))
    else:
        await message.answer(f"{message_text}")Callback.filter(F.action == "menu"))
async def show_checks_menu(callback: CallbackQuery, user: User):
    """Показать меню чеков"""
    text = f"""💳 <b>СИСТЕМА ЧЕКОВ</b>

Отправляйте GRAM монеты через специальные чеки прямо в сообщениях Telegram.

💰 Баланс: {user.balance:,.0f} GRAM

🎯 <b>ВОЗМОЖНОСТИ ЧЕКОВ:</b>
• Отправка в любой чат/канал
• Добавление комментариев и картинок
• Установка пароля для защиты
• Условие подписки для получения
• Уведомления о создании и активации"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_checks_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(CheckCallback.filter(F.action == "create_menu"))
async def show_create_menu(callback: CallbackQuery):
    """Показать меню создания чека"""
    text = """➕ <b>СОЗДАНИЕ ЧЕКА</b>

Выберите тип чека:

👤 <b>Персональный чек</b>
• Для одного получателя
• Можно указать конкретного пользователя
• Максимальная безопасность

👥 <b>Мульти-чек</b>
• Для нескольких получателей
• Можно установить лимит активаций
• Отлично для раздач

🎁 <b>Розыгрыш</b>
• Случайное распределение
• Разные суммы для каждого
• Интерактивные функции"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_check_type_keyboard()
    )
    await callback.answer()

@router.callback_query(CheckCallback.filter(F.action == "create"))
async def start_check_creation(
    callback: CallbackQuery,
    callback_data: CheckCallback,
    state: FSMContext,
    user: User
):
    """Начать создание чека"""
    check_type = callback_data.check_type
    
    # Проверяем баланс
    if user.available_balance < 10:  # Минимум 10 GRAM
        await callback.answer("❌ Недостаточно средств (минимум 10 GRAM)", show_alert=True)
        return
    
    # Устанавливаем состояние
    await state.set_state(CheckCreationStates.entering_amount)
    await state.update_data(check_type=check_type)
    
    # Названия типов
    type_names = {
        "personal": "👤 Персональный чек",
        "multi": "👥 Мульти-чек",
        "giveaway": "🎁 Розыгрыш"
    }
    
    type_name = type_names.get(check_type, "Чек")
    
    text = f"""💳 <b>СОЗДАНИЕ ЧЕКА</b>

🎯 <b>Тип:</b> {type_name}

Введите общую сумму чека в GRAM:

💡 <b>Рекомендации:</b>
• Минимум: 10 GRAM
• Доступно: {user.available_balance:,.0f} GRAM
• Учитывайте комиссию сервиса

❌ <i>Для отмены отправьте /cancel</i>"""
    
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard())
    await callback.answer()

@router.message(CheckCreationStates.entering_amount)
async def process_check_amount(message: Message, state: FSMContext, user: User):
    """Обработка суммы чека"""
    try:
        amount = Decimal(message.text.strip())
    except (ValueError, TypeError):
        await message.answer("❌ Введите корректную сумму\n\nПопробуйте еще раз:")
        return
    
    if amount < 10:
        await message.answer("❌ Минимальная сумма: 10 GRAM\n\nПопробуйте еще раз:")
        return
    
    if amount > user.available_balance:
        await message.answer(f"❌ Недостаточно средств\n\nДоступно: {user.available_balance:,.0f} GRAM\n\nПопробуйте еще раз:")
        return
    
    # Сохраняем сумму
    await state.update_data(amount=amount)
    await state.set_state(CheckCreationStates.entering_activations)
    
    data = await state.get_data()
    check_type = data["check_type"]
    
    if check_type == "personal":
        # Для персонального чека сразу переходим к настройкам
        await state.update_data(max_activations=1)
        await state.set_state(CheckCreationStates.entering_comment)
        
        text = f"""💳 <b>СОЗДАНИЕ ПЕРСОНАЛЬНОГО ЧЕКА</b>

✅ <b>Сумма:</b> {amount:,.0f} GRAM
✅ <b>Получателей:</b> 1

Введите комментарий к чеку (необязательно):

💡 <b>Примеры:</b>
• "Спасибо за помощь!"
• "Бонус за активность"
• "Подарок от друга"

⏭️ <i>Для пропуска отправьте "-"</i>
❌ <i>Для отмены отправьте /cancel</i>"""
        
        await message.answer(text)
    else:
        text = f"""💳 <b>СОЗДАНИЕ МУЛЬТИ-ЧЕКА</b>

✅ <b>Общая сумма:</b> {amount:,.0f} GRAM

Введите количество активаций (получателей):

💡 <b>Рекомендации:</b>
• Минимум: 2 активации
• Максимум: 1000 активаций
• Каждый получит: {amount:,.0f} ÷ количество

❌ <i>Для отмены отправьте /cancel</i>"""
        
        await message.answer(text)

@router.message(CheckCreationStates.entering_activations)
async def process_check_activations(message: Message, state: FSMContext):
    """Обработка количества активаций"""
    try:
        activations = int(message.text.strip())
    except (ValueError, TypeError):
        await message.answer("❌ Введите корректное число\n\nПопробуйте еще раз:")
        return
    
    if activations < 2:
        await message.answer("❌ Минимум активаций: 2\n\nПопробуйте еще раз:")
        return
    
    if activations > 1000:
        await message.answer("❌ Максимум активаций: 1000\n\nПопробуйте еще раз:")
        return
    
    data = await state.get_data()
    amount = data["amount"]
    amount_per_activation = amount / activations
    
    if amount_per_activation < 1:
        await message.answer(f"❌ Слишком много активаций\n\nПри {activations} активациях каждый получит {amount_per_activation:.2f} GRAM\nМинимум на активацию: 1 GRAM\n\nПопробуйте еще раз:")
        return
    
    # Сохраняем количество
    await state.update_data(max_activations=activations)
    await state.set_state(CheckCreationStates.entering_comment)
    
    text = f"""💳 <b>СОЗДАНИЕ МУЛЬТИ-ЧЕКА</b>

✅ <b>Общая сумма:</b> {amount:,.0f} GRAM
✅ <b>Активаций:</b> {activations}
✅ <b>На активацию:</b> {amount_per_activation:,.0f} GRAM

Введите комментарий к чеку (необязательно):

💡 <b>Примеры:</b>
• "Раздача для подписчиков!"
• "Бонус за активность в канале"
• "Новогодний подарок"

⏭️ <i>Для пропуска отправьте "-"</i>
❌ <i>Для отмены отправьте /cancel</i>"""
    
    await message.answer(text)

@router.message(CheckCreationStates.entering_comment)
async def process_check_comment(message: Message, state: FSMContext):
    """Обработка комментария чека"""
    comment = message.text.strip()
    
    if comment == "-":
        comment = None
    elif len(comment) > 200:
        await message.answer("❌ Комментарий слишком длинный (максимум 200 символов)\n\nПопробуйте еще раз:")
        return
    
    # Сохраняем комментарий
    await state.update_data(description=comment)
    await state.set_state(CheckCreationStates.entering_password)
    
    text = """🔒 <b>ПАРОЛЬ ДЛЯ ЧЕКА</b>

Установите пароль для защиты чека (необязательно):

💡 <b>Зачем нужен пароль:</b>
• Дополнительная защита
• Ограничение доступа
• Раздача только определенным людям

⏭️ <i>Для пропуска отправьте "-"</i>
❌ <i>Для отмены отправьте /cancel</i>"""
    
    await message.answer(text)

@router.message(CheckCreationStates.entering_password)
async def process_check_password(message: Message, state: FSMContext, user: User, check_service: CheckService):
    """Обработка пароля и создание чека"""
    password = message.text.strip()
    
    if password == "-":
        password = None
    elif len(password) > 50:
        await message.answer("❌ Пароль слишком длинный (максимум 50 символов)\n\nПопробуйте еще раз:")
        return
    
    # Получаем все данные
    data = await state.get_data()
    
    check_type = CheckType(data["check_type"])
    amount = data["amount"]
    max_activations = data["max_activations"]
    description = data.get("description")
    
    # Создаем чек
    check = await check_service.create_check(
        creator_id=user.telegram_id,
        check_type=check_type,
        total_amount=amount,
        max_activations=max_activations,
        description=description,
        password=password,
        expires_in_hours=24 * 7  # 7 дней
    )
    
    if check:
        amount_per_activation = amount / max_activations
        
        text = f"""✅ <b>ЧЕК СОЗДАН!</b>

💳 <b>Код чека:</b> <code>{check.check_code}</code>
💰 <b>Сумма:</b> {amount:,.0f} GRAM
👥 <b>Активаций:</b> {max_activations}
🎁 <b>На активацию:</b> {amount_per_activation:,.0f} GRAM

🔗 <b>Как поделиться:</b>
• Отправьте код другим пользователям
• Используйте кнопку "Поделиться" 
• Активация: <code>/check {check.check_code}</code>

⏰ <b>Срок действия:</b> 7 дней"""
        
        if password:
            text += f"\n🔒 <b>Пароль:</b> <code>{password}</code>"
        
        if description:
            text += f"\n💬 <b>Комментарий:</b> {description}"
        
        await message.answer(
            text,
            reply_markup=get_check_management_keyboard(check)
        )
        
        await state.clear()
    else:
        await message.answer("❌ Не удалось создать чек. Попробуйте позже.")
        await state.clear()

@router.callback_query(CheckCallback.filter(F.action == "my_checks"))
async def show_my_checks(
    callback: CallbackQuery,
    callback_data: CheckCallback,
    user: User,
    check_service: CheckService
):
    """Показать мои чеки"""
    page = callback_data.page
    limit = 10
    offset = (page - 1) * limit
    
    checks = await check_service.get_user_checks(
        user.telegram_id,
        limit=limit + 1,
        offset=offset
    )
    
    has_next = len(checks) > limit
    if has_next:
        checks = checks[:limit]
    
    if not checks:
        text = """📋 <b>МОИ ЧЕКИ</b>

📭 У вас пока нет созданных чеков.

Создайте свой первый чек:
• Выберите тип чека
• Настройте параметры
• Поделитесь с друзьями!"""
    else:
        text = f"""📋 <b>МОИ ЧЕКИ</b>

📊 Всего: {len(checks)} | Страница: {page}

Выберите чек для управления:"""
    
    keyboard = get_my_checks_keyboard(checks, page, has_next)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(CheckCallback.filter(F.action == "manage"))
async def manage_check(
    callback: CallbackQuery,
    callback_data: CheckCallback,
    check_service: CheckService
):
    """Управление чеком"""
    check_id = callback_data.check_id
    
    # Получаем аналитику чека
    analytics = await check_service.get_check_analytics(check_id)
    
    if not analytics:
        await callback.answer("❌ Чек не найден", show_alert=True)
        return
    
    check = analytics['check']
    
    # Статус чека
    status_icons = {
        "active": "🟢 Активный",
        "expired": "⏰ Истек",
        "completed": "✅ Завершен",
        "cancelled": "❌ Отменен"
    }
    
    status_text = status_icons.get(check.status, "❓ Неизвестно")
    
    text = f"""💳 <b>УПРАВЛЕНИЕ ЧЕКОМ</b>

🆔 <b>Код:</b> <code>{check.check_code}</code>
📊 <b>Статус:</b> {status_text}
💰 <b>Сумма:</b> {check.amount_per_activation:,.0f} GRAM за активацию

📈 <b>ПРОГРЕСС:</b>
├ Активировано: {check.current_activations}/{check.max_activations}
├ Процент: {analytics['completion_percentage']:.1f}%
└ Осталось: {check.remaining_activations}

💳 <b>ФИНАНСЫ:</b>
├ Общая сумма: {check.total_amount:,.0f} GRAM
├ Распределено: {analytics['total_distributed']:,.0f} GRAM
└ Остается: {check.remaining_amount:,.0f} GRAM

📅 <b>Создан:</b> {check.created_at.strftime('%d.%m.%Y %H:%M')}"""
    
    if check.expires_at:
        text += f"\n⏰ <b>Истекает:</b> {check.expires_at.strftime('%d.%m.%Y %H:%M')}"
    
    if check.description:
        text += f"\n💬 <b>Комментарий:</b> {check.description}"
    
    keyboard = get_check_management_keyboard(check)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(CheckCallback.filter(F.action == "activate"))
async def show_activate_form(callback: CallbackQuery):
    """Показать форму активации чека"""
    text = """🎫 <b>АКТИВАЦИЯ ЧЕКА</b>

Отправьте код чека для активации:

💡 <b>Как активировать:</b>
• Введите 8-значный код чека
• Или используйте команду: <code>/check КОД</code>
• Если чек с паролем, введите: <code>КОД пароль</code>

🔍 <b>Пример:</b>
• <code>AB12CD34</code>
• <code>AB12CD34 mypassword</code>

❌ <i>Для отмены отправьте /cancel</i>"""
    
    await callback.message.edit_text(text, reply_markup=get_check_activation_keyboard())
    await callback.answer()

@router.message(Command("check"))
async def cmd_activate_check(message: Message, user: User, check_service: CheckService):
    """Команда /check для активации"""
    args = message.text.split()
    
    if len(args) < 2:
        await message.answer("❌ Введите код чека: /check КОД")
        return
    
    check_code = args[1].upper()
    password = args[2] if len(args) > 2 else None
    
    # Активируем чек
    success, message_text, amount = await check_service.activate_check(
        check_code, user.telegram_id, password
    )
    
    if success:
        text = f"""🎉 <b>ЧЕК АКТИВИРОВАН!</b>

💰 Получено: <b>{amount:,.0f} GRAM</b>
🆔 Код: <code>{check_code}</code>

💳 Средства зачислены на ваш баланс!"""
        
        await message.answer(text, reply_markup=get_main_menu_keyboard(user))
    else:
        await message.answer(f"{message_text}")

@router.callback_query(Check
