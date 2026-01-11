from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from database import init_db, User, Order, get_session, get_or_create_user, create_order, get_user_orders
from config import ADMIN_IDS, ADMIN_USERNAME, CURRENCY, REFERRAL_PERCENT, REFERRAL_PERCENT_PREMIUM, \
    MIN_REFERRALS_FOR_PREMIUM

# Инициализация базы данных
engine = init_db()


class OrderForm(StatesGroup):
    bot_type = State()
    functionality = State()
    target_audience = State()
    budget = State()
    preferences = State()


def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Оставить заказ")],
            [KeyboardButton(text="📊 Партнёрская программа"), KeyboardButton(text="📋 Мои заказы")],
            [KeyboardButton(text="🆘 Помощь")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )


def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_bot_type_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Информационный", callback_data="type_info")],
            [InlineKeyboardButton(text="🎮 Игровой", callback_data="type_game")],
            [InlineKeyboardButton(text="🛒 Магазин", callback_data="type_shop")],
            [InlineKeyboardButton(text="📞 Поддержка", callback_data="type_support")],
            [InlineKeyboardButton(text="📈 Автоворонка", callback_data="type_funnel")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ]
    )


async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    args = message.text.split()
    referral_code = args[1] if len(args) > 1 else None

    session = get_session(engine)
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    if not user:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )

        if referral_code and referral_code.isdigit():
            referrer = session.query(User).filter_by(id=int(referral_code)).first()
            if referrer:
                user.referral_id = referrer.id
                referrer.is_partner = True
                user.is_partner = True

        session.add(user)
        session.commit()

    session.close()

    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "🤖 Я бот для заказа Telegram-ботов под ключ.\n\n"
        "✨ Что я могу:\n"
        "• 🛒 Создать бота для вас по индивидуальному заказу\n"
        "• 📊 Подключить вас к партнёрской программе\n"
        "• ⚡ Быстрое исполнение заказа (от 3 дней)\n\n"
        "📌 Выберите действие ниже:",
        reply_markup=get_main_keyboard()
    )


async def cmd_help(message: Message):
    await message.answer(
        f"🆘 Помощь по боту:\n\n"
        f"🛒 Как сделать заказ:\n"
        f"1. Нажмите 'Оставить заказ'\n"
        f"2. Заполните анкету (5 вопросов)\n"
        f"3. Администратор свяжется с вами в течение 24 часов\n\n"
        f"📊 Партнёрская программа:\n"
        f"• {REFERRAL_PERCENT}% с первого заказа реферала\n"
        f"• {REFERRAL_PERCENT_PREMIUM}% если привели {MIN_REFERRALS_FOR_PREMIUM}+ клиентов\n"
        f"• Выплаты в течение 3 дней после выполнения заказа\n\n"
        f"📞 Контакты: @{ADMIN_USERNAME}"
    )


async def show_partner_program(message: Message):
    session = get_session(engine)
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    if not user:
        session.close()
        await message.answer("Сначала нажмите /start")
        return

    # Статистика
    referrals_count = session.query(User).filter_by(referral_id=user.id).count()
    partner_orders = session.query(Order).filter_by(partner_id=user.id).all()
    completed_orders = [o for o in partner_orders if o.status == 'completed']
    pending_payments = sum(o.amount * o.partner_percent / 100 for o in completed_orders if not o.partner_paid)
    total_earnings = sum(o.amount * o.partner_percent / 100 for o in completed_orders if o.partner_paid)

    bot = await message.bot.get_me()
    referral_link = f"https://t.me/{bot.username}?start={user.id}"

    partner_text = f"""📊 Партнёрская программа

👤 Ваш партнёрский ID: {user.id}
🔗 Ваша реферальная ссылка:
{referral_link}

💰 Условия программы:
• {REFERRAL_PERCENT}% с первого заказа каждого реферала
• {REFERRAL_PERCENT_PREMIUM}% если привели {MIN_REFERRALS_FOR_PREMIUM}+ клиентов
• Выплаты в течение 3 дней после выполнения заказа

📈 Ваша статистика:
• Приведено клиентов: {referrals_count}
• Выполненных заказов: {len(completed_orders)}
• Ожидает выплаты: {pending_payments:.0f}{CURRENCY}
• Всего заработано: {total_earnings:.0f}{CURRENCY}

Чтобы стать партнёром, просто поделитесь своей ссылкой!"""

    session.close()

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="📋 Копировать реферальную ссылку",
        callback_data=f"copy_ref_{user.id}"
    ))
    await message.answer(partner_text, reply_markup=builder.as_markup())


async def show_my_orders(message: Message):
    session = get_session(engine)
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    if not user:
        session.close()
        await message.answer("Сначала нажмите /start")
        return

    orders = session.query(Order).filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()
    session.close()

    if not orders:
        await message.answer("📭 У вас пока нет заказов.")
        return

    for order in orders:
        status_info = {
            'new': ('🆕', 'Новый'),
            'in_progress': ('⏳', 'В работе'),
            'completed': ('✅', 'Выполнен'),
            'paid': ('💰', 'Оплачен')
        }
        emoji, status_text = status_info.get(order.status, ('📄', order.status))

        order_text = f"""📋 Заказ #{order.id}
━━━━━━━━━━━━━━
📅 Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}
📊 Тип бота: {order.bot_type}
⚡ Статус: {emoji} {status_text}
💰 Сумма: {order.amount:.0f}{CURRENCY}
━━━━━━━━━━━━━━
🎯 Функционал:
{order.functionality[:200]}{'...' if len(order.functionality) > 200 else ''}

👥 Целевая аудитория:
{order.target_audience[:200]}{'...' if len(order.target_audience) > 200 else ''}"""

        await message.answer(order_text)


async def start_order(message: Message, state: FSMContext):
    await message.answer(
        "🎯 Вы начали оформление заказа на создание бота!\n\n"
        "📝 Сначала выберите тип бота:",
        reply_markup=get_bot_type_keyboard()
    )
    await state.set_state(OrderForm.bot_type)


async def process_bot_type(callback: CallbackQuery, state: FSMContext):
    if callback.data == "cancel":
        await state.clear()
        await callback.message.answer("❌ Создание заказа отменено.", reply_markup=get_main_keyboard())
        return

    bot_types = {
        "type_info": "Информационный",
        "type_game": "Игровой",
        "type_shop": "Магазин",
        "type_support": "Поддержка",
        "type_funnel": "Автоворонка"
    }

    bot_type = bot_types.get(callback.data)
    if bot_type:
        await state.update_data(bot_type=bot_type)
        await callback.message.edit_text(f"✅ Выбран тип: {bot_type}")
        await callback.message.answer(
            "📝 Теперь опишите основной функционал бота:\n"
            "(например: прием заказов, отправка уведомлений, игра и т.д.)",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(OrderForm.functionality)


async def process_functionality(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Создание заказа отменено.", reply_markup=get_main_keyboard())
        return

    await state.update_data(functionality=message.text)
    await message.answer(
        "✅ Функционал сохранен!\n\n"
        "👥 Опишите целевую аудиторию вашего бота:\n"
        "(например: предприниматели, геймеры, студенты и т.д.)",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(OrderForm.target_audience)


async def process_target_audience(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Создание заказа отменено.", reply_markup=get_main_keyboard())
        return

    await state.update_data(target_audience=message.text)
    await message.answer(
        "✅ Целевая аудитория сохранена!\n\n"
        f"💰 Теперь укажите ваш бюджет на создание бота (в {CURRENCY}):\n"
        "(например: 50000, 100000, 150000 и т.д.)",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(OrderForm.budget)


async def process_budget(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Создание заказа отменено.", reply_markup=get_main_keyboard())
        return

    try:
        budget = float(message.text.replace(',', '.'))
        if budget < 10000:
            await message.answer(f"❌ Минимальный бюджет 10000{CURRENCY}. Введите снова:")
            return
        if budget > 10000000:
            await message.answer(f"❌ Слишком большая сумма. Введите сумму до 10,000,000{CURRENCY}:")
            return
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число (например: 50000)")
        return

    await state.update_data(budget=budget)
    await message.answer(
        f"✅ Бюджет {budget:.0f}{CURRENCY} сохранен!\n\n"
        "✨ Теперь укажите дополнительные пожелания:\n"
        "(например: дизайн, интеграции, сроки и т.д.)",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(OrderForm.preferences)


async def process_preferences(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Создание заказа отменено.", reply_markup=get_main_keyboard())
        return

    await state.update_data(preferences=message.text)
    data = await state.get_data()

    session = get_session(engine)
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    # Создаём заказ
    order = Order(
        user_id=user.id,
        bot_type=data['bot_type'],
        functionality=data['functionality'],
        target_audience=data['target_audience'],
        preferences=data['preferences'],
        amount=data['budget']
    )

    # Проверяем реферала
    if user.referral_id:
        order.partner_id = user.referral_id
        referrals_count = session.query(User).filter_by(referral_id=user.referral_id).count()
        order.partner_percent = REFERRAL_PERCENT_PREMIUM if referrals_count >= MIN_REFERRALS_FOR_PREMIUM else REFERRAL_PERCENT

        # Создаём запись о выплате
        payment = PartnerPayment(
            partner_id=user.referral_id,
            order_id=order.id,
            amount=order.amount * order.partner_percent / 100,
            percent=order.partner_percent
        )
        session.add(payment)

    session.add(order)
    session.commit()

    # Уведомление админам
    admin_text = f"""🚨 НОВЫЙ ЗАКАЗ #{order.id}
━━━━━━━━━━━━━━━━━
👤 Клиент: {user.first_name} (@{user.username or 'нет'})
📅 Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}
📊 Тип бота: {order.bot_type}
💰 Бюджет: {order.amount:.0f}{CURRENCY}
━━━━━━━━━━━━━━━━━
⚡ Функционал:
{order.functionality[:500]}{'...' if len(order.functionality) > 500 else ''}

👥 Целевая аудитория:
{order.target_audience[:500]}{'...' if len(order.target_audience) > 500 else ''}"""

    if order.partner_id:
        partner = session.query(User).filter_by(id=order.partner_id).first()
        if partner:
            admin_text += f"\n\n👥 Партнёр: {partner.first_name} (@{partner.username or 'нет'})"
            admin_text += f"\n💰 Процент: {order.partner_percent}% ({order.amount * order.partner_percent / 100:.0f}{CURRENCY})"

    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(admin_id, admin_text)
        except Exception as e:
            print(f"Ошибка отправки админу {admin_id}: {e}")

    # Подтверждение пользователю
    await message.answer(
        f"🎉 Заказ успешно создан!\n\n"
        f"📋 Номер вашего заказа: #{order.id}\n"
        f"💰 Бюджет заказа: {order.amount:.0f}{CURRENCY}\n"
        f"⏳ Администратор свяжется с вами в течение 24 часов.\n\n"
        f"📞 По вопросам: @{ADMIN_USERNAME}",
        reply_markup=get_main_keyboard()
    )

    session.close()
    await state.clear()


async def copy_referral_link(callback: CallbackQuery):
    user_id = callback.data.split('_')[-1]
    bot = await callback.bot.get_me()
    link = f"https://t.me/{bot.username}?start={user_id}"
    await callback.answer(f"Ссылка скопирована!\n{link}", show_alert=True)


async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ Действие отменено.", reply_markup=get_main_keyboard())


def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, F.text == "🆘 Помощь")
    dp.message.register(start_order, F.text == "🛒 Оставить заказ")
    dp.message.register(show_partner_program, F.text == "📊 Партнёрская программа")
    dp.message.register(show_my_orders, F.text == "📋 Мои заказы")

    dp.callback_query.register(process_bot_type, OrderForm.bot_type)
    dp.message.register(process_functionality, OrderForm.functionality)
    dp.message.register(process_target_audience, OrderForm.target_audience)
    dp.message.register(process_budget, OrderForm.budget)
    dp.message.register(process_preferences, OrderForm.preferences)

    dp.callback_query.register(copy_referral_link, F.data.startswith("copy_ref_"))
    dp.callback_query.register(cancel_action, F.data == "cancel")

    @dp.message()
    async def other_messages(message: Message, state: FSMContext):
        current_state = await state.get_state()
        if not current_state:

            await message.answer("Используйте кнопки меню:", reply_markup=get_main_keyboard())

