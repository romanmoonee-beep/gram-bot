from aiogram import Router, F
from aiogram.types import (
    CallbackQuery, Message, PreCheckoutQuery, SuccessfulPayment, 
    LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
)
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from decimal import Decimal
import uuid
import hashlib
import hmac

from app.database.models.user import User
from app.services.user_service import UserService
from app.services.transaction_service import TransactionService
from app.bot.keyboards.profile import ProfileCallback, get_deposit_keyboard
from app.bot.keyboards.payments import PaymentCallback, get_payment_confirmation_keyboard
from app.bot.keyboards.main_menu import get_main_menu_keyboard
from app.bot.utils.messages import get_deposit_text, get_success_message
from app.config.settings import settings

router = Router()

# ==================== TELEGRAM STARS PAYMENT ====================

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
            title=f"💰 Пополнение баланса - {package['title']}",
            description=description,
            payload=f"stars_deposit_{package_name}_{user.telegram_id}_{uuid.uuid4().hex[:8]}",
            provider_token="",  # Для Telegram Stars не нужен
            currency="XTR",  # Валюта Telegram Stars
            prices=prices,
            start_parameter=f"deposit_{package_name}",
            photo_url="https://i.imgur.com/your_logo.png",  # Логотип (опционально)
            photo_width=512,
            photo_height=512,
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            send_phone_number_to_provider=False,
            send_email_to_provider=False,
            is_flexible=False,
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
    payload = pre_checkout_query.invoice_payload
    
    if not payload.startswith("stars_deposit_"):
        await pre_checkout_query.answer(ok=False, error_message="Некорректный платеж")
        return
    
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

# ==================== CRYPTOBOT PAYMENT ====================

# CryptoBot пакеты
CRYPTOBOT_PACKAGES = {
    "crypto_basic": {
        "amount": 5.0,  # USD
        "currency": "USDT",
        "gram": 5000,
        "title": "💎 Crypto Basic",
        "description": "5 USDT → 5,000 GRAM"
    },
    "crypto_standard": {
        "amount": 20.0,
        "currency": "USDT", 
        "gram": 22000,  # +10% бонус
        "title": "💎 Crypto Standard",
        "description": "20 USDT → 22,000 GRAM (+10%)"
    },
    "crypto_premium": {
        "amount": 50.0,
        "currency": "USDT",
        "gram": 60000,  # +20% бонус
        "title": "💎 Crypto Premium", 
        "description": "50 USDT → 60,000 GRAM (+20%)"
    },
    "crypto_vip": {
        "amount": 100.0,
        "currency": "USDT",
        "gram": 130000,  # +30% бонус
        "title": "💎 Crypto VIP",
        "description": "100 USDT → 130,000 GRAM (+30%)"
    }
}

@router.callback_query(ProfileCallback.filter(F.action == "crypto_deposit"))
async def show_crypto_packages(callback: CallbackQuery):
    """Показать пакеты CryptoBot"""
    builder = InlineKeyboardBuilder()
    
    for package_name, package_data in CRYPTOBOT_PACKAGES.items():
        builder.row(
            InlineKeyboardButton(
                text=f"{package_data['title']} - {package_data['amount']} {package_data['currency']}",
                callback_data=PaymentCallback(action="crypto", package=package_name).pack()
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=ProfileCallback(action="deposit").pack()
        )
    )
    
    text = """💎 <b>ОПЛАТА КРИПТОВАЛЮТОЙ</b>

Выберите пакет для оплаты через @CryptoBot:

💰 <b>Принимаем:</b>
• USDT (TRC20/ERC20)
• BTC, ETH, TON
• И другие криптовалюты

⚡ <b>Преимущества:</b>
• Анонимные платежи
• Низкие комиссии
• Быстрое зачисление"""
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(PaymentCallback.filter(F.action == "crypto"))
async def create_crypto_invoice(
    callback: CallbackQuery,
    callback_data: PaymentCallback,
    user: User
):
    """Создать инвойс в CryptoBot"""
    package_name = callback_data.package
    package = CRYPTOBOT_PACKAGES.get(package_name)
    
    if not package:
        await callback.answer("❌ Пакет не найден", show_alert=True)
        return
    
    # Генерируем уникальный payload
    payload = f"crypto_{package_name}_{user.telegram_id}_{uuid.uuid4().hex[:8]}"
    
    # Создаем инвойс через CryptoBot API
    crypto_invoice_data = {
        "currency_type": "crypto",
        "asset": package["currency"],
        "amount": str(package["amount"]),
        "description": f"Пополнение PR GRAM Bot - {package['gram']:,} GRAM",
        "payload": payload,
        "return_url": f"https://t.me/{settings.BOT_USERNAME}",
        "paid_btn_name": "callback",
        "paid_btn_url": f"https://t.me/{settings.BOT_USERNAME}?start=payment_success"
    }
    
    # В реальном проекте здесь будет API запрос к CryptoBot
    # Пока что создаем кнопку для перехода в CryptoBot
    
    builder = InlineKeyboardBuilder()
    
    # Кнопка оплаты (в реальности будет URL от CryptoBot API)
    crypto_payment_url = f"https://t.me/CryptoBot?start=pay_{payload}"
    builder.row(
        InlineKeyboardButton(
            text=f"💎 Оплатить {package['amount']} {package['currency']}",
            url=crypto_payment_url
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🔄 Проверить оплату",
            callback_data=PaymentCallback(action="check_crypto", package=payload).pack()
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=ProfileCallback(action="crypto_deposit").pack()
        )
    )
    
    text = f"""💎 <b>ОПЛАТА КРИПТОВАЛЮТОЙ</b>

📦 <b>Пакет:</b> {package['title']}
💰 <b>Стоимость:</b> {package['amount']} {package['currency']}
🎁 <b>Получите:</b> {package['gram']:,} GRAM

📱 <b>Как оплатить:</b>
1. Нажмите "Оплатить" ниже
2. Следуйте инструкциям CryptoBot
3. После оплаты нажмите "Проверить оплату"

⚡ <i>Зачисление в течение 5-10 минут</i>"""
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(PaymentCallback.filter(F.action == "check_crypto"))
async def check_crypto_payment(
    callback: CallbackQuery,
    callback_data: PaymentCallback,
    user: User,
    transaction_service: TransactionService,
    user_service: UserService
):
    """Проверить статус криптоплатежа"""
    payload = callback_data.package
    
    # В реальном проекте здесь будет проверка через CryptoBot API
    # Пока что эмулируем успешную оплату для тестирования
    
    # Парсим payload для получения пакета
    try:
        parts = payload.split("_")
        package_name = f"{parts[1]}_{parts[2]}"  # crypto_basic, crypto_standard, etc.
        user_id = int(parts[3])
        
        if user_id != user.telegram_id:
            await callback.answer("❌ Ошибка проверки платежа", show_alert=True)
            return
        
        package = CRYPTOBOT_PACKAGES.get(package_name)
        if not package:
            await callback.answer("❌ Пакет не найден", show_alert=True)
            return
        
        # Проверяем, не обработан ли уже этот платеж
        existing = await transaction_service.get_transaction_by_stars_id(payload)
        if existing:
            await callback.answer("✅ Платеж уже обработан", show_alert=True)
            return
        
        # Здесь в реальности будет API запрос к CryptoBot для проверки статуса
        # Пока что для тестирования сразу засчитываем как оплаченный
        
        # Создаем транзакцию
        transaction = await transaction_service.create_transaction(
            user_id=user.telegram_id,
            amount=Decimal(str(package["gram"])),
            transaction_type="deposit_crypto",
            description=f"Пополнение через CryptoBot: {package['amount']} {package['currency']} → {package['gram']:,} GRAM",
            reference_id=payload,
            reference_type="cryptobot",
            stars_transaction_id=payload  # Используем как уникальный ID
        )
        
        if transaction:
            # Обновляем баланс пользователя
            await user_service.update_balance(
                user.telegram_id,
                Decimal(str(package["gram"])),
                "deposit_crypto",
                f"Пополнение через CryptoBot: {package['gram']:,} GRAM"
            )
            
            updated_user = await user_service.get_user(user.telegram_id)
            
            success_text = f"""🎉 <b>КРИПТОПЛАТЕЖ ОБРАБОТАН!</b>

💎 Оплачено: {package['amount']} {package['currency']}
💰 Зачислено: {package['gram']:,} GRAM
💳 Ваш баланс: {updated_user.balance:,.0f} GRAM

✨ Спасибо за пополнение!"""
            
            await callback.message.edit_text(
                success_text,
                reply_markup=get_main_menu_keyboard(updated_user)
            )
            await callback.answer("🎉 Платеж успешно обработан!")
        else:
            await callback.answer("❌ Ошибка при обработке платежа", show_alert=True)
            
    except Exception as e:
        print(f"Crypto payment check error: {e}")
        await callback.answer("❌ Ошибка проверки платежа", show_alert=True)

# ==================== БАЛАНСЫ И КОМАНДЫ ====================

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

# Тестовый обработчик для отладки (только в DEBUG режиме)
@router.callback_query(F.data == "test_payment")
async def test_payment_handler(callback: CallbackQuery, user: User, transaction_service: TransactionService):
    """Тестовый обработчик платежей (только для разработки)"""
    if not settings.DEBUG:
        await callback.answer("❌ Недоступно в продакшн режиме", show_alert=True)
        return
    
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
        await callback.answer("❌ Ошибка тестового пополнения", show_alert=True)
