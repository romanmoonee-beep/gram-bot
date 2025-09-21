from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from decimal import Decimal

from app.database.models.user import User
from app.services.settings_service import SettingsService
from app.bot.keyboards.main_menu import MainMenuCallback, get_main_menu_keyboard

router = Router()

# Callback данные для настроек
from aiogram.filters.callback_data import CallbackData

class SettingsCallback(CallbackData, prefix="settings"):
    action: str
    setting: str = "none"
    value: str = "none"

async def get_settings_keyboard(user_id: int, settings_service: SettingsService):
    """Клавиатура настроек"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    # Основные настройки
    builder.row(
        InlineKeyboardButton(
            text="🔔 Уведомления",
            callback_data=SettingsCallback(action="notifications").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🌐 Язык",
            callback_data=SettingsCallback(action="language").pack()
        ),
        InlineKeyboardButton(
            text="🔒 Приватность",
            callback_data=SettingsCallback(action="privacy").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="💸 Автовывод",
            callback_data=SettingsCallback(action="auto_withdraw").pack()
        ),
        InlineKeyboardButton(
            text="🔐 Безопасность",
            callback_data=SettingsCallback(action="security").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="📥 Экспорт настроек",
            callback_data=SettingsCallback(action="export").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🏠 В главное меню",
            callback_data=MainMenuCallback(action="main_menu").pack()
        )
    )
    
    return builder.as_markup()

async def get_notifications_keyboard(user_id: int, settings_service: SettingsService):
    """Клавиатура настроек уведомлений"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    settings = await settings_service.get_user_settings(user_id)
    
    builder = InlineKeyboardBuilder()
    
    # Уведомления о заданиях
    task_status = "✅ ВКЛ" if settings.task_notifications else "❌ ВЫКЛ"
    builder.row(
        InlineKeyboardButton(
            text=f"🎯 Задания: {task_status}",
            callback_data=SettingsCallback(
                action="toggle", 
                setting="tasks", 
                value="off" if settings.task_notifications else "on"
            ).pack()
        )
    )
    
    # Уведомления о платежах
    payment_status = "✅ ВКЛ" if settings.payment_notifications else "❌ ВЫКЛ"
    builder.row(
        InlineKeyboardButton(
            text=f"💰 Платежи: {payment_status}",
            callback_data=SettingsCallback(
                action="toggle",
                setting="payments",
                value="off" if settings.payment_notifications else "on"
            ).pack()
        )
    )
    
    # Уведомления о рефералах
    referral_status = "✅ ВКЛ" if settings.referral_notifications else "❌ ВЫКЛ"
    builder.row(
        InlineKeyboardButton(
            text=f"👥 Рефералы: {referral_status}",
            callback_data=SettingsCallback(
                action="toggle",
                setting="referrals",
                value="off" if settings.referral_notifications else "on"
            ).pack()
        )
    )
    
    # Админские уведомления
    admin_status = "✅ ВКЛ" if settings.admin_notifications else "❌ ВЫКЛ"
    builder.row(
        InlineKeyboardButton(
            text=f"👨‍💼 Админ: {admin_status}",
            callback_data=SettingsCallback(
                action="toggle",
                setting="admin",
                value="off" if settings.admin_notifications else "on"
            ).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к настройкам",
            callback_data=SettingsCallback(action="menu").pack()
        )
    )
    
    return builder.as_markup()

async def get_privacy_keyboard(user_id: int, settings_service: SettingsService):
    """Клавиатура настроек приватности"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    settings = await settings_service.get_user_settings(user_id)
    
    builder = InlineKeyboardBuilder()
    
    # Скрыть профиль
    profile_status = "✅ ВКЛ" if settings.hide_profile else "❌ ВЫКЛ"
    builder.row(
        InlineKeyboardButton(
            text=f"👤 Скрыть профиль: {profile_status}",
            callback_data=SettingsCallback(
                action="toggle_privacy",
                setting="hide_profile", 
                value="off" if settings.hide_profile else "on"
            ).pack()
        )
    )
    
    # Скрыть статистику
    stats_status = "✅ ВКЛ" if settings.hide_stats else "❌ ВЫКЛ"
    builder.row(
        InlineKeyboardButton(
            text=f"📊 Скрыть статистику: {stats_status}",
            callback_data=SettingsCallback(
                action="toggle_privacy",
                setting="hide_stats",
                value="off" if settings.hide_stats else "on"
            ).pack()
        )
    )
    
    # Скрыть из рейтинга
    leaderboard_status = "✅ ВКЛ" if settings.hide_from_leaderboard else "❌ ВЫКЛ"
    builder.row(
        InlineKeyboardButton(
            text=f"🏆 Скрыть из рейтинга: {leaderboard_status}",
            callback_data=SettingsCallback(
                action="toggle_privacy",
                setting="hide_from_leaderboard",
                value="off" if settings.hide_from_leaderboard else "on"
            ).pack()
        )
    )
    
    # Реферальные упоминания
    mentions_status = "✅ ВКЛ" if settings.allow_referral_mentions else "❌ ВЫКЛ"
    builder.row(
        InlineKeyboardButton(
            text=f"🔗 Реферальные упоминания: {mentions_status}",
            callback_data=SettingsCallback(
                action="toggle_privacy",
                setting="allow_referral_mentions",
                value="off" if settings.allow_referral_mentions else "on"
            ).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к настройкам",
            callback_data=SettingsCallback(action="menu").pack()
        )
    )
    
    return builder.as_markup()

@router.message(Command("settings"))
async def cmd_settings(message: Message, user: User, settings_service: SettingsService):
    """Команда /settings"""
    settings = await settings_service.get_user_settings(user.telegram_id)
    
    text = f"""⚙️ <b>НАСТРОЙКИ</b>

Настройте бота под свои предпочтения:

🔔 <b>Уведомления</b> - управление оповещениями
🌐 <b>Язык:</b> {settings.language.upper()}
🔒 <b>Приватность</b> - настройки конфиденциальности
💸 <b>Автовывод:</b> {'🟢 Включен' if settings.auto_withdraw_enabled else '🔴 Отключен'}
🔐 <b>Безопасность</b> - двухфакторная аутентификация

📊 <b>Статус профиля:</b>
├ Профиль: {'🔒 Скрыт' if settings.hide_profile else '👀 Виден'}
├ Статистика: {'🔒 Скрыта' if settings.hide_stats else '👀 Видна'}
└ В рейтинге: {'❌ Нет' if settings.hide_from_leaderboard else '✅ Да'}

💡 <i>Измените настройки для удобного использования бота</i>"""
    
    keyboard = await get_settings_keyboard(user.telegram_id, settings_service)
    
    await message.answer(text, reply_markup=keyboard)

@router.callback_query(MainMenuCallback.filter(F.action == "settings"))
async def show_settings_menu(callback: CallbackQuery, user: User, settings_service: SettingsService):
    """Показать меню настроек"""
    settings = await settings_service.get_user_settings(user.telegram_id)
    
    text = f"""⚙️ <b>НАСТРОЙКИ</b>

Настройте бота под свои предпочтения:

🔔 <b>Уведомления</b> - управление оповещениями
🌐 <b>Язык:</b> {settings.language.upper()}
🔒 <b>Приватность</b> - настройки конфиденциальности
💸 <b>Автовывод:</b> {'🟢 Включен' if settings.auto_withdraw_enabled else '🔴 Отключен'}
🔐 <b>Безопасность</b> - двухфакторная аутентификация

📊 <b>Статус профиля:</b>
├ Профиль: {'🔒 Скрыт' if settings.hide_profile else '👀 Виден'}
├ Статистика: {'🔒 Скрыта' if settings.hide_stats else '👀 Видна'}
└ В рейтинге: {'❌ Нет' if settings.hide_from_leaderboard else '✅ Да'}

💡 <i>Измените настройки для удобного использования бота</i>"""
    
    keyboard = await get_settings_keyboard(user.telegram_id, settings_service)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(SettingsCallback.filter(F.action == "menu"))
async def show_settings_menu_callback(callback: CallbackQuery, user: User, settings_service: SettingsService):
    """Показать меню настроек через callback"""
    await show_settings_menu(callback, user, settings_service)

@router.callback_query(SettingsCallback.filter(F.action == "notifications"))
async def show_notifications_settings(callback: CallbackQuery, user: User, settings_service: SettingsService):
    """Настройки уведомлений"""
    settings = await settings_service.get_user_settings(user.telegram_id)
    
    text = f"""🔔 <b>НАСТРОЙКИ УВЕДОМЛЕНИЙ</b>

Управляйте типами уведомлений:

🎯 <b>Задания:</b> {'✅ Включены' if settings.task_notifications else '❌ Отключены'}
├ Новые задания для вашего уровня
├ Завершение выполнения заданий
└ Одобрение/отклонение выполнений

💰 <b>Платежи:</b> {'✅ Включены' if settings.payment_notifications else '❌ Отключены'}
├ Успешные пополнения баланса
├ Списания за создание заданий
└ Начисления наград

👥 <b>Рефералы:</b> {'✅ Включены' if settings.referral_notifications else '❌ Отключены'}
├ Регистрация новых рефералов
├ Активность рефералов
└ Реферальные бонусы

👨‍💼 <b>Админ:</b> {'✅ Включены' if settings.admin_notifications else '❌ Отключены'}
├ Системные уведомления
├ Важные обновления
└ Технические работы

💡 <i>Нажмите на настройку чтобы изменить</i>"""
    
    keyboard = await get_notifications_keyboard(user.telegram_id, settings_service)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(SettingsCallback.filter(F.action == "language"))
async def show_language_settings(callback: CallbackQuery, user: User, settings_service: SettingsService):
    """Настройки языка"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    settings = await settings_service.get_user_settings(user.telegram_id)
    
    builder = InlineKeyboardBuilder()
    
    ru_status = "✅" if settings.language == "ru" else ""
    en_status = "✅" if settings.language == "en" else ""
    
    builder.row(
        InlineKeyboardButton(
            text=f"🇷🇺 Русский {ru_status}",
            callback_data=SettingsCallback(action="set_language", setting="language", value="ru").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text=f"🇺🇸 English {en_status}",
            callback_data=SettingsCallback(action="set_language", setting="language", value="en").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к настройкам",
            callback_data=SettingsCallback(action="menu").pack()
        )
    )
    
    text = f"""🌐 <b>ВЫБОР ЯЗЫКА</b>

Текущий язык: <b>{settings.language.upper()}</b>

Выберите язык интерфейса:

🇷🇺 <b>Русский</b> - полная поддержка
🇺🇸 <b>English</b> - в разработке

💡 <i>После смены языка интерфейс изменится</i>"""
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(SettingsCallback.filter(F.action == "privacy"))
async def show_privacy_settings(callback: CallbackQuery, user: User, settings_service: SettingsService):
    """Настройки приватности"""
    settings = await settings_service.get_user_settings(user.telegram_id)
    
    text = f"""🔒 <b>НАСТРОЙКИ ПРИВАТНОСТИ</b>

Управляйте видимостью ваших данных:

👤 <b>Скрыть профиль:</b> {'✅ Включено' if settings.hide_profile else '❌ Отключено'}
├ Скрыть информацию профиля от других пользователей
└ Профиль будет виден только вам

📊 <b>Скрыть статистику:</b> {'✅ Включено' if settings.hide_stats else '❌ Отключено'}
├ Скрыть вашу статистику выполнений
└ Заработки и активность будут приватными

🏆 <b>Скрыть из рейтинга:</b> {'✅ Включено' if settings.hide_from_leaderboard else '❌ Отключено'}
├ Не показывать в топах пользователей
└ Исключение из публичных рейтингов

🔗 <b>Реферальные упоминания:</b> {'✅ Включено' if settings.allow_referral_mentions else '❌ Отключено'}
├ Разрешить упоминания в реферальных бонусах
└ Уведомления о вашей реферальной активности

💡 <i>Эти настройки влияют на отображение в публичных разделах</i>"""
    
    keyboard = await get_privacy_keyboard(user.telegram_id, settings_service)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(SettingsCallback.filter(F.action == "auto_withdraw"))
async def show_auto_withdraw_settings(callback: CallbackQuery, user: User, settings_service: SettingsService):
    """Настройки автовывода"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    settings = await settings_service.get_user_settings(user.telegram_id)
    
    builder = InlineKeyboardBuilder()
    
    if settings.auto_withdraw_enabled:
        builder.row(
            InlineKeyboardButton(
                text="🔴 Отключить автовывод",
                callback_data=SettingsCallback(action="toggle_auto_withdraw", value="off").pack()
            )
        )
        
        builder.row(
            InlineKeyboardButton(
                text="⚙️ Изменить настройки",
                callback_data=SettingsCallback(action="setup_auto_withdraw").pack()
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="🟢 Включить автовывод",
                callback_data=SettingsCallback(action="setup_auto_withdraw").pack()
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="📋 Мои реквизиты",
            callback_data=SettingsCallback(action="my_withdraw_info").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к настройкам",
            callback_data=SettingsCallback(action="menu").pack()
        )
    )
    
    status_text = ""
    if settings.auto_withdraw_enabled:
        status_text = f"""
✅ <b>АВТОВЫВОД АКТИВЕН</b>

💰 <b>Порог:</b> {settings.auto_withdraw_threshold:,.0f} GRAM
💳 <b>Метод:</b> {settings.auto_withdraw_method or 'Не указан'}
📍 <b>Адрес:</b> {settings.auto_withdraw_address[:20] + '...' if settings.auto_withdraw_address and len(settings.auto_withdraw_address) > 20 else settings.auto_withdraw_address or 'Не указан'}

⚡ Средства автоматически выводятся при достижении порога."""
    else:
        status_text = """❌ <b>АВТОВЫВОД ОТКЛЮЧЕН</b>

Автоматический вывод средств не настроен."""
    
    text = f"""💸 <b>АВТОВЫВОД СРЕДСТВ</b>

{status_text}

🔧 <b>Доступные настройки:</b>
• Установка порога автовывода (от 100 GRAM)
• Выбор способа вывода
• Настройка реквизитов

💡 <b>Поддерживаемые методы:</b>
• 💳 Банковские карты
• 💰 Криптовалюты
• 🏦 Электронные кошельки

⚠️ <b>Внимание:</b> Проверьте правильность реквизитов!"""
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(SettingsCallback.filter(F.action == "security"))
async def show_security_settings(callback: CallbackQuery, user: User, settings_service: SettingsService):
    """Настройки безопасности"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    settings = await settings_service.get_user_settings(user.telegram_id)
    
    builder = InlineKeyboardBuilder()
    
    # Двухфакторная аутентификация
    tf_status = "🟢 ВКЛ" if settings.two_factor_enabled else "🔴 ВЫКЛ"
    builder.row(
        InlineKeyboardButton(
            text=f"🔐 2FA: {tf_status}",
            callback_data=SettingsCallback(
                action="toggle_2fa",
                value="off" if settings.two_factor_enabled else "on"
            ).pack()
        )
    )
    
    # Уведомления о входах
    login_status = "🟢 ВКЛ" if settings.login_notifications else "🔴 ВЫКЛ"
    builder.row(
        InlineKeyboardButton(
            text=f"🔔 Уведомления о входах: {login_status}",
            callback_data=SettingsCallback(
                action="toggle_login_notifications",
                value="off" if settings.login_notifications else "on"
            ).pack()
        )
    )
    
    # API доступ
    api_status = "🟢 ВКЛ" if settings.api_access_enabled else "🔴 ВЫКЛ"
    builder.row(
        InlineKeyboardButton(
            text=f"🔌 API доступ: {api_status}",
            callback_data=SettingsCallback(
                action="toggle_api",
                value="off" if settings.api_access_enabled else "on"
            ).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🔑 Сменить пароль",
            callback_data=SettingsCallback(action="change_password").pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к настройкам",
            callback_data=SettingsCallback(action="menu").pack()
        )
    )
    
    text = f"""🔐 <b>НАСТРОЙКИ БЕЗОПАСНОСТИ</b>

Защитите свой аккаунт дополнительными мерами:

🔐 <b>Двухфакторная аутентификация:</b> {'✅ Включена' if settings.two_factor_enabled else '❌ Отключена'}
├ Дополнительная защита аккаунта
├ Подтверждение важных операций
└ Защита от несанкционированного доступа

🔔 <b>Уведомления о входах:</b> {'✅ Включены' if settings.login_notifications else '❌ Отключены'}
├ Уведомления о новых сессиях
├ Подозрительная активность
└ Неудачные попытки входа

🔌 <b>API доступ:</b> {'✅ Разрешен' if settings.api_access_enabled else '❌ Запрещен'}
├ Доступ к API для разработчиков
├ Интеграция с внешними сервисами
└ Программное управление аккаунтом

💡 <i>Включение 2FA значительно повышает безопасность</i>"""
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# Обработчики переключения настроек
@router.callback_query(SettingsCallback.filter(F.action == "toggle"))
async def toggle_notification_setting(
    callback: CallbackQuery, 
    callback_data: SettingsCallback,
    user: User,
    settings_service: SettingsService
):
    """Переключить настройку уведомлений"""
    setting = callback_data.setting
    enabled = callback_data.value == "on"
    
    success = await settings_service.update_notification_setting(
        user.telegram_id, setting, enabled
    )
    
    if success:
        setting_names = {
            "tasks": "уведомления о заданиях",
            "payments": "уведомления о платежах", 
            "referrals": "уведомления о рефералах",
            "admin": "админские уведомления"
        }
        
        setting_name = setting_names.get(setting, setting)
        action_text = "включены" if enabled else "отключены"
        
        await callback.answer(f"✅ {setting_name.title()} {action_text}")
        await show_notifications_settings(callback, user, settings_service)
    else:
        await callback.answer("❌ Ошибка при сохранении настройки", show_alert=True)

@router.callback_query(SettingsCallback.filter(F.action == "toggle_privacy"))
async def toggle_privacy_setting(
    callback: CallbackQuery,
    callback_data: SettingsCallback, 
    user: User,
    settings_service: SettingsService
):
    """Переключить настройку приватности"""
    setting = callback_data.setting
    enabled = callback_data.value == "on"
    
    success = await settings_service.update_privacy_setting(
        user.telegram_id, setting, enabled
    )
    
    if success:
        setting_names = {
            "hide_profile": "скрытие профиля",
            "hide_stats": "скрытие статистики",
            "hide_from_leaderboard": "скрытие из рейтинга",
            "allow_referral_mentions": "реферальные упоминания"
        }
        
        setting_name = setting_names.get(setting, setting)
        action_text = "включено" if enabled else "отключено"
        
        await callback.answer(f"✅ {setting_name.title()} {action_text}")
        await show_privacy_settings(callback, user, settings_service)
    else:
        await callback.answer("❌ Ошибка при сохранении настройки", show_alert=True)

@router.callback_query(SettingsCallback.filter(F.action == "set_language"))
async def set_language(
    callback: CallbackQuery,
    callback_data: SettingsCallback,
    user: User,
    settings_service: SettingsService
):
    """Установить язык"""
    language = callback_data.value
    
    if language == "en":
        await callback.answer("🇺🇸 English будет доступен в будущих обновлениях", show_alert=True)
        return
    
    success = await settings_service.set_language(user.telegram_id, language)
    
    if success:
        await callback.answer(f"🌐 Язык изменен на {language.upper()}")
        await show_language_settings(callback, user, settings_service)
    else:
        await callback.answer("❌ Ошибка при смене языка", show_alert=True)

@router.callback_query(SettingsCallback.filter(F.action == "toggle_2fa"))
async def toggle_two_factor(
    callback: CallbackQuery,
    callback_data: SettingsCallback,
    user: User,
    settings_service: SettingsService
):
    """Переключить двухфакторную аутентификацию"""
    enabled = callback_data.value == "on"
    
    if enabled:
        # В реальном приложении здесь будет процесс настройки 2FA
        await callback.answer("🔐 Настройка 2FA будет доступна в обновлении", show_alert=True)
        return
    
    success = await settings_service.enable_two_factor(user.telegram_id, enabled)
    
    if success:
        action_text = "включена" if enabled else "отключена"
        await callback.answer(f"🔐 Двухфакторная аутентификация {action_text}")
        await show_security_settings(callback, user, settings_service)
    else:
        await callback.answer("❌ Ошибка при изменении настройки", show_alert=True)

@router.callback_query(SettingsCallback.filter(F.action == "export"))
async def export_settings(
    callback: CallbackQuery,
    user: User,
    settings_service: SettingsService
):
    """Экспорт настроек"""
    settings_data = await settings_service.export_user_settings(user.telegram_id)
    
    # Формируем читаемый текст настроек
    export_text = f"""📥 <b>ЭКСПОРТ НАСТРОЕК</b>

👤 <b>Пользователь:</b> {user.telegram_id}
📅 <b>Дата экспорта:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}

🔔 <b>УВЕДОМЛЕНИЯ:</b>
├ Задания: {'✅' if settings_data['notifications']['tasks'] else '❌'}
├ Платежи: {'✅' if settings_data['notifications']['payments'] else '❌'}
├ Рефералы: {'✅' if settings_data['notifications']['referrals'] else '❌'}
└ Админ: {'✅' if settings_data['notifications']['admin'] else '❌'}

🔒 <b>ПРИВАТНОСТЬ:</b>
├ Скрыть профиль: {'✅' if settings_data['privacy']['hide_profile'] else '❌'}
├ Скрыть статистику: {'✅' if settings_data['privacy']['hide_stats'] else '❌'}
├ Скрыть из рейтинга: {'✅' if settings_data['privacy']['hide_from_leaderboard'] else '❌'}
└ Реферальные упоминания: {'✅' if settings_data['privacy']['allow_referral_mentions'] else '❌'}

🌐 <b>ЛОКАЛИЗАЦИЯ:</b>
├ Язык: {settings_data['localization']['language'].upper()}
└ Часовой пояс: {settings_data['localization']['timezone']}

💸 <b>АВТОВЫВОД:</b>
├ Включен: {'✅' if settings_data['auto_withdraw']['enabled'] else '❌'}
├ Порог: {settings_data['auto_withdraw']['threshold']:,.0f} GRAM
├ Метод: {settings_data['auto_withdraw']['method'] or 'Не указан'}
└ Адрес: {settings_data['auto_withdraw']['address'][:20] + '...' if settings_data['auto_withdraw']['address'] and len(settings_data['auto_withdraw']['address']) > 20 else settings_data['auto_withdraw']['address'] or 'Не указан'}

🔐 <b>БЕЗОПАСНОСТЬ:</b>
├ 2FA: {'✅' if settings_data['security']['two_factor_enabled'] else '❌'}
├ Уведомления о входах: {'✅' if settings_data['security']['login_notifications'] else '❌'}
└ API доступ: {'✅' if settings_data['security']['api_access_enabled'] else '❌'}

💾 <i>Сохраните этот текст для восстановления настроек</i>"""
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к настройкам",
            callback_data=SettingsCallback(action="menu").pack()
        )
    )
    
    await callback.message.edit_text(export_text, reply_markup=builder.as_markup())
    await callback.answer("📥 Настройки экспортированы")
