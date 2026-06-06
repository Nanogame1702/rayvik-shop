
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
from scheduler.runner import start_runner
from services import scheduled_repo

router = Router(name="broadcast_scheduler")

DEFAULT_TZ = "Europe/Moscow"

class SchedStates(StatesGroup):
    waiting_text = State()
    adding_buttons = State()
    waiting_photo = State()
    waiting_time = State()
    confirm = State()

def _admin_only(message: Message) -> bool:
    return message.from_user and message.from_user.id == ADMIN_ID

@router.message(Command("broadcast_at"))
async def cmd_broadcast_at(message: Message, state: FSMContext):
    if not _admin_only(message): 
        return
    await state.clear()
    await state.update_data(audience="all", parse_mode="HTML", keyboard_layout=[], awaiting_single_btn=False, media=None)
    await message.answer("📣 Введите текст рассылки (HTML разрешён).")
    await state.set_state(SchedStates.waiting_text)

@router.message(Command("buyers_broadcast_at"))
async def cmd_buyers_broadcast_at(message: Message, state: FSMContext):
    if not _admin_only(message): 
        return
    await state.clear()
    await state.update_data(audience="buyers", parse_mode="HTML", keyboard_layout=[], awaiting_single_btn=False, media=None)
    await message.answer("📣 Введите текст рассылки для покупателей (HTML разрешён).")
    await state.set_state(SchedStates.waiting_text)

@router.message(SchedStates.waiting_text, ~F.text.startswith("/"))
async def got_text(message: Message, state: FSMContext):
    if not _admin_only(message): 
        return
    await state.update_data(text=message.html_text or message.text or "")
    kb = _buttons_menu(preview=True, done=True, media=True)
    await message.answer("Добавим кнопки или фото? Можно до 8 URL-кнопок.\nВыберите действие:", reply_markup=kb.as_markup())
    await state.set_state(SchedStates.adding_buttons)

def _buttons_menu(preview=False, done=False, media=False) -> InlineKeyboardBuilder:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Кнопка", callback_data="btn_add")
    b.button(text="↕️ Ряды", callback_data="btn_rows")
    if media:
        b.button(text="🖼 Фото", callback_data="btn_photo")
        b.button(text="🗑 Убрать фото", callback_data="btn_photo_clear")
    if preview:
        b.button(text="👁 Предпросмотр", callback_data="btn_preview")
    if done:
        b.button(text="✅ Готово", callback_data="btn_done")
    b.adjust(2,2,2)
    return b

@router.callback_query(SchedStates.adding_buttons, F.data == "btn_add")
async def add_button(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    await callback.message.edit_text("Отправьте кнопку в формате:\n`Текст кнопки | https://example.com`", parse_mode="Markdown")
    data = await state.get_data()
    data["awaiting_single_btn"] = True
    await state.update_data(**data)
    await callback.answer()

@router.message(SchedStates.adding_buttons, ~F.text.startswith("/"))
async def handle_add_button_line(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    if message.text and message.text.startswith("/"):
        return
    data = await state.get_data()
    if not data.get("awaiting_single_btn"):
        return
    line = message.text or ""
    if "|" not in line:
        await message.answer("Неверный формат. Пример:\n`Открыть сайт | https://example.com`", parse_mode="Markdown")
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
    await message.answer("Кнопка добавлена. Что дальше?", reply_markup=_buttons_menu(preview=True, done=True, media=True).as_markup())

@router.callback_query(SchedStates.adding_buttons, F.data == "btn_rows")
async def split_rows(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    data = await state.get_data()
    data.setdefault("keyboard_layout", [])
    data["keyboard_layout"].append([])
    await state.update_data(**data)
    await callback.message.edit_text("Новая строка для кнопок создана. Добавляйте далее.", reply_markup=_buttons_menu(preview=True, done=True, media=True).as_markup())
    await callback.answer()

@router.callback_query(SchedStates.adding_buttons, F.data == "btn_photo")
async def ask_photo(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    await state.set_state(SchedStates.waiting_photo)
    await callback.message.answer("Пришлите <b>фото</b> одним сообщением (можно с подписью).", parse_mode="HTML")
    await callback.answer()

@router.message(SchedStates.waiting_photo, F.photo)
async def got_photo(message: Message, state: FSMContext):
    if not _admin_only(message):
        return
    file_id = message.photo[-1].file_id
    caption = message.html_text or message.caption or ""
    data = await state.get_data()
    data["media"] = {"type":"photo", "file_id": file_id, "caption": caption, "parse_mode":"HTML"}
    await state.update_data(**data)
    await message.answer("Фото добавлено. Вернусь в конструктор.", reply_markup=_buttons_menu(preview=True, done=True, media=True).as_markup())
    await state.set_state(SchedStates.adding_buttons)

@router.callback_query(SchedStates.adding_buttons, F.data == "btn_photo_clear")
async def clear_photo(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    data = await state.get_data()
    data["media"] = None
    await state.update_data(**data)
    await callback.message.answer("Фото убрано.", reply_markup=_buttons_menu(preview=True, done=True, media=True).as_markup())
    await callback.answer()

@router.callback_query(SchedStates.adding_buttons, F.data == "btn_preview")
async def btn_preview(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    data = await state.get_data()
    text = data.get("text","")
    layout = data.get("keyboard_layout", [])
    media = data.get("media")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn["text"], url=btn["url"]) for btn in row] for row in layout if row
    ]) if layout else None
    if media and media.get("type") == "photo" and media.get("file_id"):
        await callback.message.answer_photo(media["file_id"], caption=(media.get("caption") or text)[:1024] or "(без подписи)", parse_mode="HTML", reply_markup=kb)
    else:
        await callback.message.answer(text or "(пусто)", reply_markup=kb, disable_web_page_preview=True)
    await callback.answer("Предпросмотр отправлен рядом.")

@router.callback_query(SchedStates.adding_buttons, F.data == "btn_done")
async def btn_done(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    await callback.message.edit_text("Введите время отправки в формате `YYYY-MM-DD HH:MM` (по МСК).", parse_mode="Markdown")
    await state.set_state(SchedStates.waiting_time)
    await callback.answer()

@router.message(SchedStates.waiting_time, ~F.text.startswith("/"))
async def got_time(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    raw = (message.text or "").strip()
    try:
        local_dt = datetime.strptime(raw, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(DEFAULT_TZ))
    except ValueError:
        await message.answer("Некорректный формат. Пример: `2025-10-10 19:30`", parse_mode="Markdown")
        return
    utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
    data = await state.get_data()
    layout = data.get("keyboard_layout", [])
    media = data.get("media")
    payload = {"buttons": layout, "media": media} if media else layout
    data.update(scheduled_at_utc=utc_dt.replace(second=0, microsecond=0).isoformat(), tz=DEFAULT_TZ, payload=payload)
    await state.update_data(**data)
    audience = data.get("audience","all")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn["text"], url=btn["url"]) for btn in row] for row in layout if row
    ]) if layout else None
    if media and media.get("type") == "photo" and media.get("file_id"):
        await message.answer_photo(media["file_id"], caption=(media.get("caption") or data.get("text",""))[:1024] or "(без подписи)", parse_mode="HTML", reply_markup=kb)
    else:
        await message.answer(data.get("text","") or "(пусто)", reply_markup=kb, disable_web_page_preview=True)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    confirm = InlineKeyboardBuilder()
    confirm.button(text="✅ Запланировать", callback_data="sched_confirm")
    confirm.button(text="✏️ Изменить", callback_data="sched_edit")
    confirm.button(text="❌ Отмена", callback_data="sched_cancel")
    confirm.adjust(2,1)
    human = f"{audience.upper()} • {local_dt.strftime('%Y-%m-%d %H:%M')} МСК (UTC {utc_dt.strftime('%H:%M')})"
    await message.answer(f"⏱ Подтверждение рассылки:\n{human}", reply_markup=confirm.as_markup())
    await state.set_state(SchedStates.confirm)

@router.callback_query(SchedStates.confirm, F.data == "sched_edit")
async def sched_edit(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    await callback.message.edit_text("Вернулись к добавлению кнопок/фото.", reply_markup=_buttons_menu(preview=True, done=True, media=True).as_markup())
    await state.set_state(SchedStates.adding_buttons)
    await callback.answer()

@router.callback_query(SchedStates.confirm, F.data == "sched_cancel")
async def sched_cancel(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    await state.clear()
    await callback.message.edit_text("❌ Запланированная рассылка отменена.")
    await callback.answer()

@router.callback_query(SchedStates.confirm, F.data == "sched_confirm")
async def sched_confirm(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    data = await state.get_data()
    await scheduled_repo.ensure_schema()
    keyboard_json = json.dumps(data.get("payload"), ensure_ascii=False)
    task_id = await scheduled_repo.create(
        audience=data.get("audience","all"),
        text=data.get("text",""),
        parse_mode=data.get("parse_mode","HTML"),
        keyboard_json=keyboard_json,
        scheduled_at_utc=data.get("scheduled_at_utc"),
        tz=data.get("tz", DEFAULT_TZ),
        created_by=callback.from_user.id
    )
    await state.clear()
    await callback.message.edit_text(f"✅ Запланировано. ID: {task_id}")
    await start_runner(callback.bot, admin_chat_id=callback.from_user.id)
    await callback.answer()
