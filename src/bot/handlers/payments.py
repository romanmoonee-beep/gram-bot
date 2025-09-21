from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery, SuccessfulPayment, LabeledPrice
from aiogram.filters import Command

from app.database.models.user import User
from app.services.user_service import UserService
from app.services.transaction_service import TransactionService
from app.bot.keyboards.profile import ProfileCallback, get_deposit_keyboard
from app.bot.keyboards.payments import PaymentCallback, get_payment_confirmation_keyboard
from app.bot.keyboards.main_menu import get_main_menu_keyboard
from app.bot.utils.messages import get_deposit_text, get_success_message
from app.config.settings import settings

router = Router()

@router.callback_query(ProfileCallback.filter(F.action == "buy_stars"))
async def buy_stars_package(
    callback: CallbackQuery,
    callback_data: ProfileCallback,
    user: User
):
    """Купить пакет Stars"""
    package_name = callback_data.data
    package = settings.get_stars_package(package_name)
    
    if not package:
        await callback.answer("❌ Пакет не найден", show_alert=True)
        return
    
    # Показываем детали пакета
    text = get_deposit_text(package_name)
    keyboard = get_payment_confirmation_keyboard(package_name, package["stars"])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(PaymentCallback.filter(F.action == "confirm"))
async def confirm_stars_payment(
    callback: CallbackQuery,
    callback_data: PaymentCallback,
    user: User
):
    """Подтверждение оплаты Stars"""
    package_name = callback_data.package
    stars_amount = callback_data.amount
    
    package = settings.get_stars_package(package_name)
    if not package:
        await callback.answer("❌ Пакет не найден", show_alert=True)
        return
    
    # Рассчитываем GRAM
    base_gram, bonus_gram = settings.calculate_gram_from_stars(stars_amount, package_name)
    total_gram = base_gram + bonus_gram
    
    # Создаем инвойс для Telegram Stars
    prices = [LabeledPrice(label=package["title"], amount=stars_amount)]
    
    # Формируем описание
    description = f"Пополнение баланса: {total_gram:,.0f} GRAM"
    if bonus_gram > 0:
        description += f" (включая бонус {bonus_gram:,.0f} GRAM)"
    
    try:
        await callback.bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"Пополнение баланса - {package['title']}",
            description=description,
            payload=f"stars_deposit_{package_name}_{user.telegram_id}",
            provider_token="",  # Для Telegram Stars не нужен
            currency="XTR",  # Валюта Telegram Stars
            prices=prices,
            start_parameter=f"deposit_{package_name}",
            request_timeout=30
        )
        
        await callback.message.edit_text(
            f"""💳 <b>СЧЕТ ОТПРАВЛЕН</b>

📱 Проверьте личные сообщения от бота.
⭐ Оплатите {stars_amount} Telegram Stars
💰 Получите {total_gram:,.0f} GRAM

⚡ Зачисление происходит автоматически после оплаты!""",
            reply_markup=get_main_menu_keyboard(user)
        )
        
        await callback.answer("💳 Счет отправлен в личные сообщения!")
        
    except Exception as e:
        await callback.answer("❌ Ошибка при создании счета", show_alert=True)
        print(f"Invoice error: {e}")

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """Обработка предварительной проверки платежа"""
    # Проверяем корректность данных платежа
    payload = pre_checkout_query.invoice_payload
    
    if not payload.startswith("stars_deposit_"):
        await pre_checkout_query.answer(ok=False, error_message="Некорректный платеж")
        return
    
    # Парсим payload
    try:
        parts = payload.split("_")
        package_name = parts[2]
        user_id = int(parts[3])
        
        # Проверяем существование пакета
        package = settings.get_stars_package(package_name)
        if not package:
            await pre_checkout_query.answer(ok=False, error_message="Пакет не найден")
            return
        
        # Проверяем сумму
        if pre_checkout_query.total_amount != package["stars"]:
            await pre_checkout_query.answer(ok=False, error_message="Некорректная сумма")
            return
        
        await pre_checkout_query.answer(ok=True)
        
    except (ValueError, IndexError):
        await pre_checkout_query.answer(ok=False, error_message="Ошибка обработки платежа")

@router.message(F.successful_payment)
async def process_successful_payment(
    message: Message,
    user: User,
    transaction_service: TransactionService,
    user_service: UserService
):
    """Обработка успешного платежа"""
    payment = message.successful_payment
    payload = payment.invoice_payload
    
    try:
        # Парсим payload
        parts = payload.split("_")
        package_name = parts[2]
        user_id = int(parts[3])
        
        # Проверяем, что платеж от правильного пользователя
        if user_id != user.telegram_id:
            await message.answer("❌ Ошибка: платеж от другого пользователя")
            return
        
        # Получаем пакет
        package = settings.get_stars_package(package_name)
        if not package:
            await message.answer("❌ Ошибка: пакет не найден")
            return
        
        # Обрабатываем платеж
        transaction = await transaction_service.process_telegram_stars_payment(
            user_id=user.telegram_id,
            stars_amount=payment.total_amount,
            stars_transaction_id=payment.telegram_payment_charge_id,
            package_name=package_name
        )
        
        if transaction:
            # Рассчитываем итоговую сумму
            base_gram, bonus_gram = settings.calculate_gram_from_stars(payment.total_amount, package_name)
            total_gram = base_gram + bonus_gram
            
            # Формируем сообщение об успехе
            success_text = f"""🎉 <b>ПЛАТЕЖ УСПЕШНО ОБРАБОТАН!</b>

⭐ Оплачено: {payment.total_amount} Telegram Stars
💰 Зачислено: {total_gram:,.0f} GRAM"""
            
            if bonus_gram > 0:
                success_text += f"\n🎁 Бонус: {bonus_gram:,.0f} GRAM"
            
            # Обновляем информацию о пользователе
            updated_user = await user_service.get_user(user.telegram_id)
            success_text += f"\n\n💳 Ваш баланс: {updated_user.balance:,.0f} GRAM"
            
            success_text += "\n\n✨ Спасибо за пополнение! Теперь вы можете создавать задания или продолжить заработок."
            
            await message.answer(
                success_text,
                reply_markup=get_main_menu_keyboard(updated_user)
            )
            
        else:
            await message.answer(
                "❌ Ошибка при обработке платежа. Обратитесь в поддержку.",
                reply_markup=get_main_menu_keyboard(user)
            )
            
    except Exception as e:
        print(f"Payment processing error: {e}")
        await message.answer(
            "❌ Ошибка при обработке платежа. Обратитесь в поддержку.",
            reply_markup=get_main_menu_keyboard(user)
        )

@router.message(Command("balance"))
async def cmd_balance(message: Message, user: User):
    """Команда /balance"""
    text = f"""💰 <b>ВАШ БАЛАНС</b>

💳 Доступно: <b>{user.available_balance:,.0f} GRAM</b>
🔒 Заморожено: {user.frozen_balance:,.0f} GRAM
📊 Общий: {user.balance:,.0f} GRAM

📈 <b>СТАТИСТИКА:</b>
├ Заработано: {user.total_earned:,.0f} GRAM
├ Потрачено: {user.total_spent:,.0f} GRAM
└ Пополнено: {user.total_deposited:,.0f} GRAM

💎 Уровень: {user.get_level_config()['name']}"""
    
    await message.answer(text, reply_markup=get_deposit_keyboard())

# Дополнительные обработчики для отладки платежей
@router.callback_query(F.data == "test_payment")
async def test_payment_handler(callback: CallbackQuery, user: User):
    """Тестовый обработчик платежей (только для разработки)"""
    if not settings.DEBUG:
        await callback.answer("❌ Недоступно в продакшн режиме")
        return
    
    # Эмулируем успешный платеж для тестирования
    from app.services.transaction_service import TransactionService
    from decimal import Decimal
    
    transaction_service = TransactionService()
    
    # Тестовое начисление 1000 GRAM
    success = await transaction_service.process_telegram_stars_payment(
        user_id=user.telegram_id,
        stars_amount=100,
        stars_transaction_id=f"test_{user.telegram_id}_{callback.message.message_id}",
        package_name="basic"
    )
    
    if success:
        await callback.answer("✅ Тестовое пополнение выполнено!")
        await callback.message.edit_text(
            "✅ Тестовое пополнение на 1000 GRAM выполнено!",
            reply_markup=get_main_menu_keyboard(user)
        )
    else:
        await callback.answer("❌ Ошибка тестового пополнения")

# ==============================================================================
# app/bot/states/task_creation.py - FSM состояния создания заданий
# ==============================================================================

from aiogram.fsm.state import State, StatesGroup

class TaskCreationStates(StatesGroup):
    """Состояния для создания задания"""
    entering_title = State()
    entering_description = State()
    entering_url = State()
    entering_reward = State()
    entering_quantity = State()
    confirmation = State()

class TaskExecutionStates(StatesGroup):
    """Состояния для выполнения заданий"""
    uploading_screenshot = State()
    entering_comment = State()
    waiting_check = State()

class CheckCreationStates(StatesGroup):
    """Состояния для создания чеков"""
    entering_amount = State()
    entering_recipient = State()
    entering_comment = State()
    entering_password = State()
    confirmation = State()