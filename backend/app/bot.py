# bot.py
import asyncio
import re
from collections import defaultdict

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8211910029:AAFOIoyf8fOhVDnqKpNlEY0OS7O0Cd7jX8Y"  # в реале лучше вынести в .env

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ============================
#   СОГЛАСИЕ С УСЛОВИЯМИ
# ============================

accepted_user_ids = set()

# ============================
#       USER TARIFF MOCK
# ============================

user_tariff = {}  # user_id: "FREE" | "PRO" | "PREMIUM"


def get_user_tariff(user_id: int) -> str:
    return user_tariff.get(user_id, "FREE")


# ============================
#       ОПЕРАЦИИ ПОЛЬЗОВАТЕЛЯ
# ============================

# Список операций по пользователю
# Пример элемента: {"type": "income", "amount": 1300.0, "comment": "маникюр"}
user_operations = defaultdict(list)

# Простое состояние пользователя (для ввода суммы)
# user_states[user_id] = {"step": "await_income_amount"} | {"step": "await_expense_amount"}
user_states = {}


def build_stats_text(user_id: int) -> str:
    ops = user_operations.get(user_id, [])
    if not ops:
        return "У вас пока нет операций. Добавьте доход или расход через /income или /expense."

    from collections import defaultdict

    income_by_cat = defaultdict(float)
    expense_by_cat = defaultdict(float)

    for op in ops:
        op_type = op.get("type")
        amount = op.get("amount", 0)
        # категорию берём из комментария, если нет — считаем "Без категории"
        cat = op.get("comment") or "Без категории"

        if op_type == "income":
            income_by_cat[cat] += amount
        elif op_type == "expense":
            expense_by_cat[cat] += amount

    lines = []

    # Доходы по категориям
    if income_by_cat:
        lines.append("Доходы:")
        for cat, amount in income_by_cat.items():
            lines.append(f"- {cat}: {amount:.2f} ₽")
        lines.append("")  # пустая строка-разделитель

    # Расходы по категориям
    if expense_by_cat:
        lines.append("Расходы:")
        for cat, amount in expense_by_cat.items():
            lines.append(f"- {cat}: {amount:.2f} ₽")
        lines.append("")

    total_income = sum(income_by_cat.values())
    total_expense = sum(expense_by_cat.values())
    balance = total_income - total_expense

    lines.append(f"Общий доход: {total_income:.2f} ₽")
    lines.append(f"Общие расходы: {total_expense:.2f} ₽")
    lines.append(f"Баланс: {balance:.2f} ₽")

    # Текст в зависимости от плюса/минуса
    if balance > 0:
        lines.append("✅ Вы в плюсе. Так держать!")
    elif balance < 0:
        lines.append("⚠ Сейчас вы в минусе. Проверьте расходы и цены на услуги.")
    else:
        lines.append("ℹ По балансу пока ноль. Добавьте больше операций для анализа.")

    return "\n".join(lines)


def parse_category_and_amount(text: str):
    """
    Ожидаем формат: 'Категория 100' или 'Подработка по вечерам 1500'
    Берём последнее число как сумму, остальное — категория.
    """
    parts = text.strip().split()
    if not parts:
        return None, None

    # Ищем с конца первое число
    for i in range(len(parts) - 1, -1, -1):
        token = parts[i].replace(",", ".")
        # число типа 100 или 100.50
        if re.fullmatch(r"\d+(\.\d{1,2})?", token):
            try:
                amount = float(token)
            except ValueError:
                continue

            category = " ".join(parts[:i]).strip()
            if not category:
                category = "Без категории"

            return category, amount

    return None, None



# ============================
#   ВСПОМОГАТЕЛЬНОЕ: ТАРИФЫ
# ============================

def get_tariffs_text() -> str:
    return (
        "Выберите уровень:\n\n"
        "FREE — чат: быстрый учёт доходов/расходов.\n"
        "PRO — 499 ₽/мес: Mini App, формы и категории, CRM-клиенты, напоминания, аналитика, экспорт, шаблоны договоров.\n"
        "PREMIUM — 999 ₽/мес: всё из PRO + ИИ-прогнозы и умные напоминания + 1 консультация/мес (юрист/бухгалтер/налоговая).\n\n"
        "Начните с PRO — апгрейд до PREMIUM в один тап, когда понадобится ИИ и эксперты."
    )


def get_tariffs_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Оформить PRO — 499 ₽",
                    callback_data="tariff_pro"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Оформить PREMIUM — 999 ₽",
                    callback_data="tariff_premium"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Сравнить тарифы",
                    callback_data="tariff_compare"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Остаться на FREE",
                    callback_data="tariff_free"
                )
            ],
        ]
    )


# ============================
#   ВСПОМОГАТЕЛЬНОЕ: HELP
# ============================

def get_help_text_and_keyboard(user_id: int):
    tariff = get_user_tariff(user_id)

    if tariff == "FREE":
        text = (
            "Ваш тариф: FREE\n"
            "Что уже умеем: запись доходов/расходов и базовая сводка.\n"
            "Чтобы добавить клиентов, напоминания и экспорт — откройте PRO.\n\n"
            "Быстрый старт:\n"
            "• Внести: доход 1300 / расход материалы 450\n"
            "• Итоги: итоги неделя / итоги месяц\n"
            "• Поддержка: /support"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Команды", callback_data="hp_cmd")],
                [InlineKeyboardButton(text="Как вносить операции", callback_data="hp_ops")],
                [InlineKeyboardButton(text="Открыть подписки", callback_data="sub_back")],
                [InlineKeyboardButton(text="Поддержка", callback_data="hp_support")],
            ]
        )

    elif tariff == "PRO":
        text = (
            "Ваш тариф: PRO\n"
            "Доступно: формы ввода, категории, клиенты, напоминания, экспорт.\n"
            "Хотите ИИ-прогнозы и 1 консультацию/мес — откройте PREMIUM.\n\n"
            "Полезно:\n"
            "• Экспорт в Excel/PDF: /export\n"
            "• Клиент + запись: клиент Иванова + запись 15:00 завтра\n"
            "• Напоминания клиентам: напомнить Ивановой за 2 часа\n"
            "• Поддержка: /support"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Команды", callback_data="hp_cmd")],
                [InlineKeyboardButton(text="Экспорт", callback_data="hp_export")],
                [InlineKeyboardButton(text="Клиенты", callback_data="hp_clients")],
                [InlineKeyboardButton(text="Напоминания", callback_data="hp_remind")],
                [InlineKeyboardButton(text="Открыть подписки", callback_data="sub_back")],
                [InlineKeyboardButton(text="Поддержка", callback_data="hp_support")],
            ]
        )

    else:  # PREMIUM
        text = (
            "Ваш тариф: PREMIUM\n"
            "У вас полный доступ: ИИ-прогнозы, умные напоминания, расширенная аналитика, "
            "1 консультация/мес (юрист/бухгалтер/налоги).\n\n"
            "Полезно:\n"
            "• Прогнозы: прогноз выручки на месяц\n"
            "• Аналитика: где теряю деньги?\n"
            "• Консультация: запросить консультацию\n"
            "• Поддержка: /support"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Команды", callback_data="hp_cmd")],
                [InlineKeyboardButton(text="Экспорт", callback_data="hp_export")],
                [InlineKeyboardButton(text="Клиенты", callback_data="hp_clients")],
                [InlineKeyboardButton(text="Напоминания", callback_data="hp_remind")],
                [InlineKeyboardButton(text="Поддержка", callback_data="hp_support")],
            ]
        )

    return text, keyboard


# ============================
#           /start
# ============================

@dp.message(CommandStart())
async def start_command(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принять соглашение",
                    callback_data="accept_terms"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data="decline_terms"
                ),
            ]
        ]
    )

    await message.answer(
        "Привет! Перед началом работы с ботом нужно принять пользовательское соглашение.\n\n"
        "Нажмите «Принять соглашение», чтобы продолжить.",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "accept_terms")
async def accept_terms(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    accepted_user_ids.add(user_id)

    await callback.message.edit_text(
        "✅ Вы приняли пользовательское соглашение.\n"
        "Теперь можете пользоваться ботом."
    )
    await callback.answer()


@dp.callback_query(F.data == "decline_terms")
async def decline_terms(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "❌ Вы отказались от пользовательского соглашения.\n"
        "Если передумаете — отправьте /start ещё раз."
    )
    await callback.answer()


# ============================
#         /tariffs, /subscribe
# ============================

@dp.message(Command("subscribe"))
async def subscribe_command(message: types.Message):
    await message.answer(
        get_tariffs_text(),
        reply_markup=get_tariffs_keyboard()
    )


@dp.callback_query(F.data == "sub_back")
async def sub_back(callback: types.CallbackQuery):
    await callback.message.edit_text(
        get_tariffs_text(),
        reply_markup=get_tariffs_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "tariff_pro")
async def tariff_pro(callback: types.CallbackQuery):
    await callback.answer(
        "Оформление PRO пока в разработке. Сейчас это демо-кнопка.",
        show_alert=True
    )


@dp.callback_query(F.data == "tariff_premium")
async def tariff_premium(callback: types.CallbackQuery):
    await callback.answer(
        "Оформление PREMIUM пока в разработке. Сейчас это демо-кнопка.",
        show_alert=True
    )


@dp.callback_query(F.data == "tariff_compare")
async def tariff_compare(callback: types.CallbackQuery):
    await callback.answer(
        "Экран сравнения тарифов будет добавлен позже.",
        show_alert=True
    )


@dp.callback_query(F.data == "tariff_free")
async def tariff_free(callback: types.CallbackQuery):
    await callback.answer(
        "Вы остались на FREE. Можно пользоваться базовым функционалом.",
        show_alert=True
    )


# ============================
#           /help
# ============================

@dp.message(Command("help"))
async def help_command(message: types.Message):
    uid = message.from_user.id
    text, keyboard = get_help_text_and_keyboard(uid)
    await message.answer(text, reply_markup=keyboard)


# HELP CALLBACKS

@dp.callback_query(F.data == "hp_cmd")
async def hp_commands(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Команды:\n"
        "/start — запуск\n"
        "/help — помощь\n"
        "/income — добавить доход\n"
        "/expense — добавить расход\n"
        "/operations — экран операций\n"
        "/clients — клиенты и записи\n"
        "/remind — напоминания\n"
        "/analytics — аналитика\n"
        "/export — экспорт\n"
        "/subscribe — подписка\n"
        "/settings — настройки\n"
        "/support — поддержка\n"
        "/experts — эксперты (для PREMIUM)",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="← Назад", callback_data="help_back")]
            ]
        )
    )
    await callback.answer()


@dp.callback_query(F.data == "hp_ops")
async def hp_ops(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Как вносить операции:\n"
        "• доход 1300\n"
        "• расход маникюр 900\n"
        "• итоги неделя / итоги месяц",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="← Назад", callback_data="help_back")]
            ]
        )
    )
    await callback.answer()


@dp.callback_query(F.data == "hp_export")
async def hp_export(callback: types.CallbackQuery):
    uid = callback.from_user.id
    tariff = get_user_tariff(uid)

    if tariff == "FREE":
        text = "Экспорт доступен в PRO. Откройте PRO, чтобы выгружать Excel и PDF."
    else:
        text = (
            "Экспорт:\n"
            "• /export — выбор формата\n"
            "• Excel, PDF, e-mail\n"
            "• Можно выбрать период"
        )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="← Назад", callback_data="help_back")]
            ]
        )
    )
    await callback.answer()


@dp.callback_query(F.data == "hp_clients")
async def hp_clients(callback: types.CallbackQuery):
    uid = callback.from_user.id
    tariff = get_user_tariff(uid)

    if tariff == "FREE":
        text = "Клиенты и записи доступны в PRO."
    else:
        text = (
            "Клиенты:\n"
            "• Добавить клиента: клиент Иванова\n"
            "• Создать запись: запись 15:00 завтра\n"
            "• Напоминания клиентам"
        )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="← Назад", callback_data="help_back")]
            ]
        )
    )
    await callback.answer()


@dp.callback_query(F.data == "hp_remind")
async def hp_remind(callback: types.CallbackQuery):
    uid = callback.from_user.id
    tariff = get_user_tariff(uid)

    if tariff == "FREE":
        text = "Напоминания доступны в PRO."
    elif tariff == "PRO":
        text = (
            "Напоминания:\n"
            "• напомнить Ивановой за 2 часа\n"
            "• автоматические напоминания — в Mini App"
        )
    else:
        text = (
            "Умные ИИ-напоминания:\n"
            "• выбирают время автоматически\n"
            "• учитывают тип услуги и историю клиента"
        )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="← Назад", callback_data="help_back")]
            ]
        )
    )
    await callback.answer()


@dp.callback_query(F.data == "hp_support")
async def hp_support(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Поддержка:\nНапишите ваш вопрос — мы ответим в рабочее время.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="← Назад", callback_data="help_back")]
            ]
        )
    )
    await callback.answer()


@dp.callback_query(F.data == "hp_faq")
async def hp_faq(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "FAQ:\nЧастые вопросы: оплата, экспорт, клиенты, напоминания…\n"
        "Эта секция будет доработана позже.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="← Назад", callback_data="help_back")]]
        )
    )
    await callback.answer()


@dp.callback_query(F.data == "hp_tour")
async def hp_tour(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Быстрый старт (3 шага):\n"
        "1️⃣ Создайте категории.\n"
        "2️⃣ Добавьте клиента.\n"
        "3️⃣ Внесите первую операцию: доход или расход.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="← Назад", callback_data="help_back")]]
        )
    )
    await callback.answer()


@dp.callback_query(F.data == "hp_bug")
async def hp_bug(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Сообщить об ошибке:\n"
        "Кратко опишите проблему, приложите скрин — отправлю отчёт разработчикам.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="← Назад", callback_data="help_back")]]
        )
    )
    await callback.answer()


@dp.callback_query(F.data == "help_back")
async def help_back(callback: types.CallbackQuery):
    uid = callback.from_user.id
    text, keyboard = get_help_text_and_keyboard(uid)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# ============================
#      /income и /expense
# ============================

@dp.message(Command("income"))
async def income_command(message: types.Message):
    uid = message.from_user.id
    user_states[uid] = {"step": "await_income_amount"}

    await message.answer(
        "Добавление дохода.\n"
        "Введите доход в формате:\n"
        "Подработка 100"
    )



@dp.message(Command("expense"))
async def expense_command(message: types.Message):
    uid = message.from_user.id
    user_states[uid] = {"step": "await_expense_amount"}

    await message.answer(
        "Добавление расхода.\n"
        "Введите расход в формате:\n"
        "Материалы 400"
    )



# ============================
#          /operations
# ============================

def get_operations_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Доход", callback_data="op_income"),
                InlineKeyboardButton(text="Расход", callback_data="op_expense"),
            ],
            [
                InlineKeyboardButton(text="Категория", callback_data="op_cat"),
                InlineKeyboardButton(text="Клиент", callback_data="op_client"),
            ],
            [
                InlineKeyboardButton(text="Фото чека", callback_data="op_receipt"),
            ],
            [
                InlineKeyboardButton(text="Сохранить", callback_data="op_save"),
                InlineKeyboardButton(text="Отменить", callback_data="op_cancel"),
            ],
        ]
    )


@dp.message(Command("operations"))
async def operations_command(message: types.Message):
    await message.answer(
        "Главный экран — Операции.\nЧто делаем?",
        reply_markup=get_operations_keyboard()
    )


@dp.callback_query(F.data == "op_income")
async def op_income(callback: types.CallbackQuery):
    uid = callback.from_user.id
    user_states[uid] = {"step": "await_income_amount"}

    await callback.message.answer(
        "Введите доход в формате: Подработка 100"
    )
    await callback.answer()



@dp.callback_query(F.data == "op_expense")
async def op_expense(callback: types.CallbackQuery):
    uid = callback.from_user.id
    user_states[uid] = {"step": "await_expense_amount"}

    await callback.message.answer(
        "Введите расход в формате: Материалы 400"
    )
    await callback.answer()



@dp.callback_query(F.data == "op_cat")
async def op_cat(callback: types.CallbackQuery):
    await callback.message.answer(
        "Категория: Выберите категорию или напишите новую. (Заглушка, логика добавится позже.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "op_client")
async def op_client(callback: types.CallbackQuery):
    await callback.message.answer(
        "Клиент: Укажите клиента — начните вводить ФИО/телефон. (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "op_receipt")
async def op_receipt(callback: types.CallbackQuery):
    await callback.message.answer(
        "Пришлите фото чека — прикрепим к операции. (Пока без сохранения в БД.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "op_save")
async def op_save(callback: types.CallbackQuery):
    await callback.message.answer(
        "Готово! Операция сохранена ✅ (пока заглушка, сохранение по шагам добавим позже)."
    )
    await callback.answer()


@dp.callback_query(F.data == "op_cancel")
async def op_cancel(callback: types.CallbackQuery):
    uid = callback.from_user.id
    user_states.pop(uid, None)
    await callback.message.answer(
        "Отменил. Ничего не сохранено."
    )
    await callback.answer()


# ============================
#           /clients
# ============================

def get_clients_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Записать", callback_data="cl_book"),
                InlineKeyboardButton(text="Напомнить", callback_data="cl_remind"),
            ],
            [
                InlineKeyboardButton(text="Ссылка в календарь", callback_data="cl_ics"),
            ],
            [
                InlineKeyboardButton(text="История", callback_data="cl_history"),
                InlineKeyboardButton(text="Шаблон сообщения", callback_data="cl_template"),
            ],
        ]
    )


@dp.message(Command("clients"))
async def clients_command(message: types.Message):
    await message.answer(
        "Клиенты.\n(В будущем здесь будет список клиентов и выбор карточки.)",
        reply_markup=get_clients_keyboard()
    )


@dp.callback_query(F.data == "cl_book")
async def cl_book(callback: types.CallbackQuery):
    await callback.message.answer(
        "Записать: Выберите дату и время — пришлю ссылку для календаря. (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "cl_remind")
async def cl_remind(callback: types.CallbackQuery):
    await callback.message.answer(
        "Когда напомнить клиенту? Выберите пресет или введите дату/время. (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "cl_ics")
async def cl_ics(callback: types.CallbackQuery):
    await callback.message.answer(
        "Готово! Вот ссылка для календаря клиента: {url}\n(Пока заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "cl_history")
async def cl_history(callback: types.CallbackQuery):
    await callback.message.answer(
        "Последние операции по клиенту: … (Заглушка, позже подтянем реальные данные.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "cl_template")
async def cl_template(callback: types.CallbackQuery):
    await callback.message.answer(
        "Скопируйте и отправьте:\n"
        "«Здравствуйте, {name}! Ваша запись {date} {time}…» (Заглушка.)"
    )
    await callback.answer()


# ============================
#           /remind
# ============================

def get_remind_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Сегодня", callback_data="bk_today"),
                InlineKeyboardButton(text="Завтра", callback_data="bk_tomorrow"),
            ],
            [
                InlineKeyboardButton(text="Выбрать дату", callback_data="bk_date"),
            ],
            [
                InlineKeyboardButton(text="Создать ICS", callback_data="bk_make_ics"),
                InlineKeyboardButton(text="Отправить ссылку", callback_data="bk_send_link"),
            ],
        ]
    )


@dp.message(Command("remind"))
async def remind_command(message: types.Message):
    await message.answer(
        "Записи / Напоминания. Выберите вариант:",
        reply_markup=get_remind_keyboard()
    )


@dp.callback_query(F.data == "bk_today")
async def bk_today(callback: types.CallbackQuery):
    await callback.message.answer(
        "Запись создана на сегодня в {time}. (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "bk_tomorrow")
async def bk_tomorrow(callback: types.CallbackQuery):
    await callback.message.answer(
        "Запись создана на завтра в {time}. (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "bk_date")
async def bk_date(callback: types.CallbackQuery):
    await callback.message.answer(
        "Выберите дату в календаре ниже. (Календарь добавим позже.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "bk_make_ics")
async def bk_make_ics(callback: types.CallbackQuery):
    await callback.message.answer(
        "Событие готово: {ics_link} (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "bk_send_link")
async def bk_send_link(callback: types.CallbackQuery):
    await callback.message.answer(
        "Ссылка скопирована. Отправьте её клиенту. (Заглушка.)"
    )
    await callback.answer()



@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    uid = message.from_user.id
    text = build_stats_text(uid)
    await message.answer(text)


# ============================
#           /analytics
# ============================

def get_analytics_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="День", callback_data="an_day"),
                InlineKeyboardButton(text="Неделя", callback_data="an_week"),
                InlineKeyboardButton(text="Месяц", callback_data="an_month"),
            ],
            [
                InlineKeyboardButton(text="ТОП услуги", callback_data="an_services"),
                InlineKeyboardButton(text="ТОП клиенты", callback_data="an_clients"),
            ],
            [
                InlineKeyboardButton(text="Экспорт отчёта", callback_data="an_export"),
            ],
        ]
    )


@dp.message(Command("analytics"))
async def analytics_command(message: types.Message):
    await message.answer(
        "Аналитика. Выберите период или отчёт:",
        reply_markup=get_analytics_keyboard()
    )


@dp.callback_query(F.data == "an_day")
async def an_day(callback: types.CallbackQuery):
    await callback.message.answer(
        "День: доход {sum_in}, расход {sum_out}, баланс {balance}. (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "an_week")
async def an_week(callback: types.CallbackQuery):
    await callback.message.answer(
        "Неделя: … График и ТОП-категории доступны в PRO. (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "an_month")
async def an_month(callback: types.CallbackQuery):
    await callback.message.answer(
        "Месяц: … Прогноз тренда доступен в PREMIUM (ИИ). (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "an_services")
async def an_services(callback: types.CallbackQuery):
    await callback.message.answer(
        "ТОП услуг за период: … (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "an_clients")
async def an_clients(callback: types.CallbackQuery):
    await callback.message.answer(
        "ТОП клиентов за период: … (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "an_export")
async def an_export(callback: types.CallbackQuery):
    await callback.message.answer(
        "Выберите формат: Excel / PDF / Период. (Заглушка.)"
    )
    await callback.answer()


# ============================
#            /export
# ============================

def get_export_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Excel", callback_data="ex_xlsx"),
                InlineKeyboardButton(text="PDF", callback_data="ex_pdf"),
            ],
            [
                InlineKeyboardButton(text="Период", callback_data="ex_period"),
                InlineKeyboardButton(text="Отправить на e-mail", callback_data="ex_email"),
            ],
        ]
    )


@dp.message(Command("export"))
async def export_command(message: types.Message):
    await message.answer(
        "Экспорт отчёта. Выберите формат:",
        reply_markup=get_export_keyboard()
    )


@dp.callback_query(F.data == "ex_xlsx")
async def ex_xlsx(callback: types.CallbackQuery):
    await callback.message.answer(
        "Готово: отчёт Excel за {period}. (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "ex_pdf")
async def ex_pdf(callback: types.CallbackQuery):
    await callback.message.answer(
        "Готово: отчёт PDF за {period}. (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "ex_period")
async def ex_period(callback: types.CallbackQuery):
    await callback.message.answer(
        "Укажите диапазон дат (напр. 01.10–31.10). (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "ex_email")
async def ex_email(callback: types.CallbackQuery):
    await callback.message.answer(
        "Введите e-mail. Отправлю отчёт после подтверждения. (Заглушка.)"
    )
    await callback.answer()


# ============================
#          /subscribe (меню)
# ============================

def get_subscribe_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="FREE", callback_data="sb_free"),
            ],
            [
                InlineKeyboardButton(text="PRO — 499 ₽/мес", callback_data="sb_pro"),
            ],
            [
                InlineKeyboardButton(text="PREMIUM — 999 ₽/мес", callback_data="sb_premium"),
            ],
            [
                InlineKeyboardButton(text="7 дней PRO", callback_data="sb_trial"),
            ],
            [
                InlineKeyboardButton(text="Оплатить PRO", callback_data="sb_pay_pro"),
                InlineKeyboardButton(text="Оплатить PREMIUM", callback_data="sb_pay_premium"),
            ],
            [
                InlineKeyboardButton(text="Промокод", callback_data="sb_promo"),
                InlineKeyboardButton(text="Отменить автооплату", callback_data="sb_cancel"),
            ],
        ]
    )


@dp.message(Command("subscribe"))
async def subscribe_main_command(message: types.Message):
    await message.answer(
        "Подписка и тарифы. Выберите опцию:",
        reply_markup=get_subscribe_keyboard()
    )


@dp.callback_query(F.data == "sb_free")
async def sb_free(callback: types.CallbackQuery):
    await callback.message.answer(
        "Вы на FREE — чат-ввод, базовые функции. Обновитесь до PRO, чтобы открыть Mini App и CRM. (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "sb_pro")
async def sb_pro(callback: types.CallbackQuery):
    await callback.message.answer(
        "PRO: Mini App, формы, категории, CRM, напоминания, аналитика, экспорт. Оформить? (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "sb_premium")
async def sb_premium(callback: types.CallbackQuery):
    await callback.message.answer(
        "PREMIUM: всё из PRO + ИИ-прогнозы/напоминания + 1 консультация/мес (юрист/бухгалтер/налоги). Подключить? (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "sb_trial")
async def sb_trial(callback: types.CallbackQuery):
    await callback.message.answer(
        "Активировал PRO-триал на 7 дней. Напомню за сутки до окончания. (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "sb_pay_pro")
async def sb_pay_pro(callback: types.CallbackQuery):
    await callback.message.answer(
        "Счёт на PRO: {pay_link} (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "sb_pay_premium")
async def sb_pay_premium(callback: types.CallbackQuery):
    await callback.message.answer(
        "Счёт на PREMIUM: {pay_link} (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "sb_promo")
async def sb_promo(callback: types.CallbackQuery):
    await callback.message.answer(
        "Введите промокод одним сообщением. (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "sb_cancel")
async def sb_cancel(callback: types.CallbackQuery):
    await callback.message.answer(
        "Автопродление отключено. Доступ активен до {date}. (Заглушка.)"
    )
    await callback.answer()


# ============================
#           /settings
# ============================

def get_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Профиль", callback_data="st_profile"),
                InlineKeyboardButton(text="Категории", callback_data="st_categories"),
            ],
            [
                InlineKeyboardButton(text="Налоговый режим", callback_data="st_tax"),
            ],
            [
                InlineKeyboardButton(text="Интеграции", callback_data="st_integrations"),
                InlineKeyboardButton(text="Резервное копирование", callback_data="st_backup"),
            ],
        ]
    )


@dp.message(Command("settings"))
async def settings_command(message: types.Message):
    await message.answer(
        "Настройки. Что хотите изменить?",
        reply_markup=get_settings_keyboard()
    )


@dp.callback_query(F.data == "st_profile")
async def st_profile(callback: types.CallbackQuery):
    await callback.message.answer(
        "Профиль открыт. Обновите ИНН/телефон/почту. (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "st_categories")
async def st_categories(callback: types.CallbackQuery):
    await callback.message.answer(
        "Выберите категорию или добавьте новую. (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "st_tax")
async def st_tax(callback: types.CallbackQuery):
    await callback.message.answer(
        "Текущий режим: {mode}. Изменить? (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "st_integrations")
async def st_integrations(callback: types.CallbackQuery):
    await callback.message.answer(
        "Доступные интеграции: Google Календарь, e-mail. Выберите. (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "st_backup")
async def st_backup(callback: types.CallbackQuery):
    await callback.message.answer(
        "Резервное копирование: Скачать бэкап / Восстановить из файла. (Заглушка.)"
    )
    await callback.answer()


# ============================
#           /support
# ============================

def get_support_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="FAQ", callback_data="hp_faq"),
                InlineKeyboardButton(text="Быстрый старт (3 шага)", callback_data="hp_tour"),
            ],
            [
                InlineKeyboardButton(text="Написать оператору", callback_data="hp_support"),
            ],
            [
                InlineKeyboardButton(text="Сообщить об ошибке", callback_data="hp_bug"),
            ],
        ]
    )


@dp.message(Command("support"))
async def support_command(message: types.Message):
    await message.answer(
        "Поддержка. Что вам нужно?",
        reply_markup=get_support_keyboard()
    )


# ============================
#           /experts
# ============================

def get_experts_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Вопрос юристу", callback_data="ex_lawyer"),
            ],
            [
                InlineKeyboardButton(text="Консультация бухгалтера", callback_data="ex_cfo"),
            ],
            [
                InlineKeyboardButton(text="Статус заявки", callback_data="ex_status"),
            ],
        ]
    )


@dp.message(Command("experts"))
async def experts_command(message: types.Message):
    await message.answer(
        "Эксперты (доступно для PREMIUM). Пока тестовый режим.",
        reply_markup=get_experts_keyboard()
    )


@dp.callback_query(F.data == "ex_lawyer")
async def ex_lawyer(callback: types.CallbackQuery):
    await callback.message.answer(
        "Опишите вопрос юристу. Ответ эксперта придёт в чат / на e-mail. (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "ex_cfo")
async def ex_cfo(callback: types.CallbackQuery):
    await callback.message.answer(
        "Выберите удобное время. Доступно 1 раз в месяц. (Заглушка.)"
    )
    await callback.answer()


@dp.callback_query(F.data == "ex_status")
async def ex_status(callback: types.CallbackQuery):
    await callback.message.answer(
        "Статус: {state}. Ожидаем ответ: {eta}. (Заглушка.)"
    )
    await callback.answer()


# ============================
#   Хэндлер текста для income/expense
# ============================

@dp.message(F.text)
async def handle_text_states(message: types.Message):
    # Игнорируем команды
    if message.text.startswith("/"):
        return

    uid = message.from_user.id
    state = user_states.get(uid)

    if not state:
        # Здесь можно позже обрабатывать "доход 1300"/"расход 500" без команд
        return

    step = state.get("step")

    if step == "await_income_amount":
        category, amount = parse_category_and_amount(message.text)
        if amount is None:
            await message.answer(
                "Формат дохода: Подработка 100\n"
                "Сначала описание, потом сумма."
            )
            return

        user_operations[uid].append(
            {"type": "income", "amount": amount, "comment": category}
        )
        user_states.pop(uid, None)

        await message.answer(
            f"Доход '{category}': {amount:.2f} Р сохранён ✅"
        )


    elif step == "await_expense_amount":
        category, amount = parse_category_and_amount(message.text)
        if amount is None:
            await message.answer(
                "Формат расхода: Материалы 400\n"
                "Сначала описание, потом сумма."
            )
            return

        user_operations[uid].append(
            {"type": "expense", "amount": amount, "comment": category}
        )
        user_states.pop(uid, None)

        await message.answer(
            f"Расход '{category}': {amount:.2f} Р сохранён ✅"
        )



# ============================
#           /ping
# ============================

@dp.message(Command("ping"))
async def ping_command(message: types.Message):
    await message.answer("Бот работает")


# ============================
#          MAIN
# ============================

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
