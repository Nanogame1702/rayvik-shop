"""
Обработчик создания повторяющихся рассылок
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_ID
from database import create_recurring_broadcast
from services.recurring_service import RecurringBroadcastService

router = Router(name="recurring_broadcast")

DEFAULT_TZ = "Europe/Moscow"


class RecurringStates(StatesGroup):
    waiting_name = State()
    waiting_text = State()
    adding_buttons = State()
    waiting_photo = State()
    waiting_pattern = State()
    waiting_days = State()
    waiting_day_of_month = State()
    waiting_time = State()
    confirm = State()


def _admin_only(message: Message) -> bool:
    return message.from_user and message.from_user.id == ADMIN_ID


def _buttons_menu(preview=False, done=False, media=False) -> InlineKeyboardBuilder:
    """Меню для конструктора кнопок"""
    b = InlineKeyboardBuilder()
    b.button(text="➕ Кнопка", callback_data="rec_btn_add")
    b.button(text="↕️ Ряды", callback_data="rec_btn_rows")
    if media:
        b.button(text="🖼 Фото", callback_data="rec_btn_photo")
        b.button(text="🗑 Убрать фото", callback_data="rec_btn_photo_clear")
    if preview:
        b.button(text="👁 Предпросмотр", callback_data="rec_btn_preview")
    if done:
        b.button(text="✅ Готово", callback_data="rec_btn_done")
    b.adjust(2, 2, 2)
    return b


# ============================================================================
# КОМАНДЫ СОЗДАНИЯ
# ============================================================================

@router.message(Command("recurring_broadcast"))
async def cmd_recurring_broadcast(message: Message, state: FSMContext):
    """Создание повторяющейся рассылки для всех"""
    if not _admin_only(message):
        return
    
    await state.clear()
    await state.update_data(
        audience="all",
        parse_mode="HTML",
        keyboard_layout=[],
        awaiting_single_btn=False,
        media=None
    )
    await message.answer(
        "📣 <b>Создание повторяющейся рассылки</b>\n\n"
        "Введите название рассылки (для удобства управления):",
        parse_mode="HTML"
    )
    await state.set_state(RecurringStates.waiting_name)


@router.message(Command("recurring_buyers_broadcast"))
async def cmd_recurring_buyers_broadcast(message: Message, state: FSMContext):
    """Создание повторяющейся рассылки для покупателей"""
    if not _admin_only(message):
        return
    
    await state.clear()
    await state.update_data(
        audience="buyers",
        parse_mode="HTML",
        keyboard_layout=[],
        awaiting_single_btn=False,
        media=None
    )
    await message.answer(
        "📣 <b>Создание повторяющейся рассылки для покупателей</b>\n\n"
        "Введите название рассылки (для удобства управления):",
        parse_mode="HTML"
    )
    await state.set_state(RecurringStates.waiting_name)


# ============================================================================
# ВВОД НАЗВАНИЯ И ТЕКСТА
# ============================================================================

@router.message(RecurringStates.waiting_name, ~F.text.startswith("/"))
async def got_name(message: Message, state: FSMContext):
    """Получение названия рассылки"""
    if not _admin_only(message):
        return
    
    name = (message.text or "").strip()
    if not name or len(name) > 100:
        await message.answer("❌ Название должно быть от 1 до 100 символов")
        return
    
    await state.update_data(name=name)
    await message.answer(
        f"✅ Название: <b>{name}</b>\n\n"
        "Теперь введите текст рассылки (HTML разрешён):",
        parse_mode="HTML"
    )
    await state.set_state(RecurringStates.waiting_text)


@router.message(RecurringStates.waiting_text, ~F.text.startswith("/"))
async def got_text(message: Message, state: FSMContext):
    """Получение текста рассылки"""
    if not _admin_only(message):
        return
    
    await state.update_data(text=message.html_text or message.text or "")
    kb = _buttons_menu(preview=True, done=True, media=True)
    await message.answer(
        "Добавим кнопки или фото? Можно до 8 URL-кнопок.\nВыберите действие:",
        reply_markup=kb.as_markup()
    )
    await state.set_state(RecurringStates.adding_buttons)


# ============================================================================
# КОНСТРУКТОР КНОПОК
# ============================================================================

@router.callback_query(RecurringStates.adding_buttons, F.data == "rec_btn_add")
async def add_button(callback: CallbackQuery, state: FSMContext):
    """Добавление кнопки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "Отправьте кнопку в формате:\n`Текст кнопки | https://example.com`",
        parse_mode="Markdown"
    )
    data = await state.get_data()
    data["awaiting_single_btn"] = True
    await state.update_data(**data)
    await callback.answer()


@router.message(RecurringStates.adding_buttons, ~F.text.startswith("/"))
async def handle_add_button_line(message: Message, state: FSMContext):
    """Обработка добавления кнопки"""
    if message.from_user.id != ADMIN_ID:
        return
    if message.text and message.text.startswith("/"):
        return
    
    data = await state.get_data()
    if not data.get("awaiting_single_btn"):
        return
    
    line = message.text or ""
    if "|" not in line:
        await message.answer(
            "Неверный формат. Пример:\n`Открыть сайт | https://example.com`",
            parse_mode="Markdown"
        )
        return
    
    text, url = [part.strip() for part in line.split("|", 1)]
    if not (text and url and (url.startswith("http://") or url.startswith("https://"))):
        await message.answer("Нужны текст и корректный URL (http/https). Попробуйте ещё раз.")
        return
    
    data.setdefault("keyboard_layout", [])
    if not data["keyboard_layout"] or len(data["keyboard_layout"][-1]) >= 2:
        data["keyboard_layout"].append([])
    
    data["keyboard_layout"][-1].append({"text": text[:64], "url": url})
    
    if sum(len(r) for r in data["keyboard_layout"]) > 8:
        data["keyboard_layout"][-1].pop()
        await message.answer("Ограничение: максимум 8 кнопок.")
    
    data["awaiting_single_btn"] = False
    await state.update_data(**data)
    await message.answer(
        "Кнопка добавлена. Что дальше?",
        reply_markup=_buttons_menu(preview=True, done=True, media=True).as_markup()
    )


@router.callback_query(RecurringStates.adding_buttons, F.data == "rec_btn_rows")
async def split_rows(callback: CallbackQuery, state: FSMContext):
    """Создание новой строки кнопок"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    data = await state.get_data()
    data.setdefault("keyboard_layout", [])
    data["keyboard_layout"].append([])
    await state.update_data(**data)
    await callback.message.edit_text(
        "Новая строка для кнопок создана. Добавляйте далее.",
        reply_markup=_buttons_menu(preview=True, done=True, media=True).as_markup()
    )
    await callback.answer()


@router.callback_query(RecurringStates.adding_buttons, F.data == "rec_btn_photo")
async def ask_photo(callback: CallbackQuery, state: FSMContext):
    """Запрос фото"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    await state.set_state(RecurringStates.waiting_photo)
    await callback.message.answer(
        "Пришлите <b>фото</b> одним сообщением (можно с подписью).",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(RecurringStates.waiting_photo, F.photo)
async def got_photo(message: Message, state: FSMContext):
    """Получение фото"""
    if not _admin_only(message):
        return
    
    file_id = message.photo[-1].file_id
    caption = message.html_text or message.caption or ""
    data = await state.get_data()
    data["media"] = {
        "type": "photo",
        "file_id": file_id,
        "caption": caption,
        "parse_mode": "HTML"
    }
    await state.update_data(**data)
    await message.answer(
        "Фото добавлено. Вернусь в конструктор.",
        reply_markup=_buttons_menu(preview=True, done=True, media=True).as_markup()
    )
    await state.set_state(RecurringStates.adding_buttons)


@router.callback_query(RecurringStates.adding_buttons, F.data == "rec_btn_photo_clear")
async def clear_photo(callback: CallbackQuery, state: FSMContext):
    """Удаление фото"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    data = await state.get_data()
    data["media"] = None
    await state.update_data(**data)
    await callback.message.answer(
        "Фото убрано.",
        reply_markup=_buttons_menu(preview=True, done=True, media=True).as_markup()
    )
    await callback.answer()


@router.callback_query(RecurringStates.adding_buttons, F.data == "rec_btn_preview")
async def btn_preview(callback: CallbackQuery, state: FSMContext):
    """Предпросмотр сообщения"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    data = await state.get_data()
    text = data.get("text", "")
    layout = data.get("keyboard_layout", [])
    media = data.get("media")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn["text"], url=btn["url"]) for btn in row]
        for row in layout if row
    ]) if layout else None
    
    if media and media.get("type") == "photo" and media.get("file_id"):
        await callback.message.answer_photo(
            media["file_id"],
            caption=(media.get("caption") or text)[:1024] or "(без подписи)",
            parse_mode="HTML",
            reply_markup=kb
        )
    else:
        await callback.message.answer(
            text or "(пусто)",
            reply_markup=kb,
            disable_web_page_preview=True
        )
    await callback.answer("Предпросмотр отправлен рядом.")


# ============================================================================
# ВЫБОР РАСПИСАНИЯ
# ============================================================================

@router.callback_query(RecurringStates.adding_buttons, F.data == "rec_btn_done")
async def btn_done(callback: CallbackQuery, state: FSMContext):
    """Переход к выбору расписания"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Ежедневно", callback_data="rec_pattern_daily")
    kb.button(text="📆 Еженедельно", callback_data="rec_pattern_weekly")
    kb.button(text="📊 Ежемесячно", callback_data="rec_pattern_monthly")
    kb.adjust(1)
    
    await callback.message.edit_text(
        "⏰ Выберите частоту рассылки:",
        reply_markup=kb.as_markup()
    )
    await state.set_state(RecurringStates.waiting_pattern)
    await callback.answer()


@router.callback_query(RecurringStates.waiting_pattern, F.data.startswith("rec_pattern_"))
async def got_pattern(callback: CallbackQuery, state: FSMContext):
    """Получение паттерна расписания"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    pattern = callback.data.split("_")[-1]  # daily, weekly, monthly
    await state.update_data(schedule_pattern=pattern)
    
    if pattern == "daily":
        # Для ежедневной сразу спрашиваем время
        await callback.message.edit_text(
            "🕐 Введите время отправки в формате <code>HH:MM</code> (по МСК):\n\n"
            "Например: <code>09:00</code>",
            parse_mode="HTML"
        )
        await state.set_state(RecurringStates.waiting_time)
    
    elif pattern == "weekly":
        # Для еженедельной спрашиваем дни
        kb = InlineKeyboardBuilder()
        days = [
            ("Пн", 1), ("Вт", 2), ("Ср", 3), ("Чт", 4),
            ("Пт", 5), ("Сб", 6), ("Вс", 7)
        ]
        for day_name, day_num in days:
            kb.button(text=day_name, callback_data=f"rec_day_{day_num}")
        kb.button(text="✅ Готово", callback_data="rec_days_done")
        kb.adjust(4, 3, 1)
        
        await state.update_data(selected_days=[])
        await callback.message.edit_text(
            "📆 Выберите дни недели для рассылки (можно несколько):",
            reply_markup=kb.as_markup()
        )
        await state.set_state(RecurringStates.waiting_days)
    
    elif pattern == "monthly":
        # Для ежемесячной спрашиваем день месяца
        await callback.message.edit_text(
            "📊 Введите день месяца (1-31):\n\n"
            "Например: <code>15</code> (15 число каждого месяца)",
            parse_mode="HTML"
        )
        await state.set_state(RecurringStates.waiting_day_of_month)
    
    await callback.answer()


# ============================================================================
# ВЫБОР ДНЕЙ НЕДЕЛИ (для weekly)
# ============================================================================

@router.callback_query(RecurringStates.waiting_days, F.data.startswith("rec_day_"))
async def toggle_day(callback: CallbackQuery, state: FSMContext):
    """Переключение дня недели"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    day_num = int(callback.data.split("_")[-1])
    data = await state.get_data()
    selected_days = data.get("selected_days", [])
    
    if day_num in selected_days:
        selected_days.remove(day_num)
    else:
        selected_days.append(day_num)
    
    await state.update_data(selected_days=selected_days)
    
    # Обновляем клавиатуру с отметками
    kb = InlineKeyboardBuilder()
    days = [
        ("Пн", 1), ("Вт", 2), ("Ср", 3), ("Чт", 4),
        ("Пт", 5), ("Сб", 6), ("Вс", 7)
    ]
    for day_name, day_num_iter in days:
        mark = "✓ " if day_num_iter in selected_days else ""
        kb.button(text=f"{mark}{day_name}", callback_data=f"rec_day_{day_num_iter}")
    kb.button(text="✅ Готово", callback_data="rec_days_done")
    kb.adjust(4, 3, 1)
    
    await callback.message.edit_reply_markup(reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(RecurringStates.waiting_days, F.data == "rec_days_done")
async def days_done(callback: CallbackQuery, state: FSMContext):
    """Завершение выбора дней"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    data = await state.get_data()
    selected_days = data.get("selected_days", [])
    
    if not selected_days:
        await callback.answer("❌ Выберите хотя бы один день!", show_alert=True)
        return
    
    # Сохраняем в JSON формате
    await state.update_data(schedule_days=json.dumps(selected_days))
    
    await callback.message.edit_text(
        "🕐 Введите время отправки в формате <code>HH:MM</code> (по МСК):\n\n"
        "Например: <code>09:00</code>",
        parse_mode="HTML"
    )
    await state.set_state(RecurringStates.waiting_time)
    await callback.answer()



# ============================================================================
# ВВОД ДНЯ МЕСЯЦА (для monthly)
# ============================================================================

@router.message(RecurringStates.waiting_day_of_month, ~F.text.startswith("/"))
async def got_day_of_month(message: Message, state: FSMContext):
    """Получение дня месяца"""
    if not _admin_only(message):
        return
    
    try:
        day = int(message.text.strip())
        if not (1 <= day <= 31):
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer(
            "❌ Неверный формат. Введите число от 1 до 31.\n"
            "Например: <code>15</code>",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(schedule_day_of_month=day)
    await message.answer(
        "🕐 Введите время отправки в формате <code>HH:MM</code> (по МСК):\n\n"
        "Например: <code>09:00</code>",
        parse_mode="HTML"
    )
    await state.set_state(RecurringStates.waiting_time)


# ============================================================================
# ВВОД ВРЕМЕНИ
# ============================================================================

@router.message(RecurringStates.waiting_time, ~F.text.startswith("/"))
async def got_time(message: Message, state: FSMContext):
    """Получение времени отправки"""
    if not _admin_only(message):
        return
    
    time_str = (message.text or "").strip()
    
    # Валидация формата HH:MM
    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer(
            "❌ Неверный формат времени. Используйте <code>HH:MM</code>\n"
            "Например: <code>09:00</code>",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(schedule_time=time_str)
    
    # Показываем финальное подтверждение
    await show_confirmation(message, state)


# ============================================================================
# ФИНАЛЬНОЕ ПОДТВЕРЖДЕНИЕ
# ============================================================================

async def show_confirmation(message: Message, state: FSMContext):
    """Показ финального подтверждения"""
    data = await state.get_data()
    
    # Формируем описание расписания
    pattern = data['schedule_pattern']
    time = data['schedule_time']
    
    if pattern == 'daily':
        schedule_desc = f"📅 Каждый день в {time} МСК"
    elif pattern == 'weekly':
        days = json.loads(data.get('schedule_days', '[]'))
        day_names = {1: 'Пн', 2: 'Вт', 3: 'Ср', 4: 'Чт', 5: 'Пт', 6: 'Сб', 7: 'Вс'}
        days_str = ', '.join(day_names[d] for d in sorted(days))
        schedule_desc = f"📆 Каждую неделю: {days_str} в {time} МСК"
    else:  # monthly
        day = data.get('schedule_day_of_month')
        schedule_desc = f"📊 Каждый месяц {day} числа в {time} МСК"
    
    # Рассчитываем первую отправку
    try:
        next_send = RecurringBroadcastService.calculate_next_send_time(
            pattern=pattern,
            schedule_time=time,
            schedule_days=data.get('schedule_days'),
            day_of_month=data.get('schedule_day_of_month'),
            timezone=DEFAULT_TZ
        )
        next_send_local = next_send.astimezone(ZoneInfo(DEFAULT_TZ))
        next_send_str = next_send_local.strftime('%Y-%m-%d %H:%M')
    except Exception as e:
        await message.answer(f"❌ Ошибка расчета времени: {e}")
        return
    
    # Показываем предпросмотр сообщения
    text = data.get("text", "")
    layout = data.get("keyboard_layout", [])
    media = data.get("media")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn["text"], url=btn["url"]) for btn in row]
        for row in layout if row
    ]) if layout else None
    
    if media and media.get("type") == "photo" and media.get("file_id"):
        await message.answer_photo(
            media["file_id"],
            caption=(media.get("caption") or text)[:1024] or "(без подписи)",
            parse_mode="HTML",
            reply_markup=kb
        )
    else:
        await message.answer(
            text or "(пусто)",
            reply_markup=kb,
            disable_web_page_preview=True
        )
    
    # Кнопки подтверждения
    confirm_kb = InlineKeyboardBuilder()
    confirm_kb.button(text="✅ Создать", callback_data="rec_confirm")
    confirm_kb.button(text="📤 Тест", callback_data="rec_test")
    confirm_kb.button(text="✏️ Изменить", callback_data="rec_edit")
    confirm_kb.button(text="❌ Отмена", callback_data="rec_cancel")
    confirm_kb.adjust(2, 2)
    
    audience_text = "всех пользователей" if data.get('audience') == 'all' else "покупателей"
    
    await message.answer(
        f"⏱ <b>Подтверждение рассылки</b>\n\n"
        f"📝 Название: <b>{data['name']}</b>\n"
        f"👥 Аудитория: {audience_text}\n"
        f"{schedule_desc}\n"
        f"⏰ Первая отправка: {next_send_str} МСК",
        reply_markup=confirm_kb.as_markup(),
        parse_mode="HTML"
    )
    await state.set_state(RecurringStates.confirm)


# ============================================================================
# ОБРАБОТКА ПОДТВЕРЖДЕНИЯ
# ============================================================================

@router.callback_query(RecurringStates.confirm, F.data == "rec_test")
async def rec_test(callback: CallbackQuery, state: FSMContext):
    """Тестовая отправка админу"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    data = await state.get_data()
    text = data.get("text", "")
    layout = data.get("keyboard_layout", [])
    media = data.get("media")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn["text"], url=btn["url"]) for btn in row]
        for row in layout if row
    ]) if layout else None
    
    try:
        if media and media.get("type") == "photo" and media.get("file_id"):
            await callback.message.answer_photo(
                media["file_id"],
                caption=(media.get("caption") or text)[:1024] or "(тест)",
                parse_mode="HTML",
                reply_markup=kb
            )
        else:
            await callback.message.answer(
                f"🧪 <b>ТЕСТ</b>\n\n{text or '(пусто)'}",
                reply_markup=kb,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        await callback.answer("✅ Тест отправлен!")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.callback_query(RecurringStates.confirm, F.data == "rec_edit")
async def rec_edit(callback: CallbackQuery, state: FSMContext):
    """Возврат к редактированию"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "Вернулись к добавлению кнопок/фото.",
        reply_markup=_buttons_menu(preview=True, done=True, media=True).as_markup()
    )
    await state.set_state(RecurringStates.adding_buttons)
    await callback.answer()


@router.callback_query(RecurringStates.confirm, F.data == "rec_cancel")
async def rec_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена создания"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    await state.clear()
    await callback.message.edit_text("❌ Создание повторяющейся рассылки отменено.")
    await callback.answer()



@router.callback_query(RecurringStates.confirm, F.data == "rec_confirm")
async def rec_confirm(callback: CallbackQuery, state: FSMContext):
    """Подтверждение создания рассылки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    data = await state.get_data()
    
    try:
        # Подготавливаем keyboard_json
        layout = data.get("keyboard_layout", [])
        media = data.get("media")
        
        if media:
            keyboard_data = {"buttons": layout, "media": media}
        else:
            keyboard_data = layout
        
        keyboard_json = json.dumps(keyboard_data, ensure_ascii=False)
        
        # Создаем recurring broadcast
        recurring_id = await create_recurring_broadcast(
            name=data['name'],
            audience=data['audience'],
            text=data['text'],
            keyboard_json=keyboard_json,
            schedule_pattern=data['schedule_pattern'],
            schedule_time=data['schedule_time'],
            schedule_days=data.get('schedule_days'),
            schedule_day_of_month=data.get('schedule_day_of_month'),
            timezone=DEFAULT_TZ,
            created_by=callback.from_user.id
        )
        
        # Создаем первую задачу
        task_id = await RecurringBroadcastService.create_scheduled_task_from_recurring(recurring_id)
        
        await state.clear()
        
        if task_id:
            await callback.message.edit_text(
                f"✅ <b>Повторяющаяся рассылка создана!</b>\n\n"
                f"ID рассылки: #{recurring_id}\n"
                f"ID первой задачи: #{task_id}\n\n"
                f"Используйте /recurring_list для управления",
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                f"⚠️ <b>Рассылка создана, но не удалось создать задачу</b>\n\n"
                f"ID рассылки: #{recurring_id}\n\n"
                f"Проверьте логи или используйте /recurring_list",
                parse_mode="HTML"
            )
        
        await callback.answer("✅ Создано!")
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ <b>Ошибка при создании:</b>\n\n<code>{e}</code>",
            parse_mode="HTML"
        )
        await callback.answer("❌ Ошибка!", show_alert=True)
