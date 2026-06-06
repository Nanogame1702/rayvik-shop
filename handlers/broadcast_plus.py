
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_ID
from utils.broadcast_sender import send_broadcast

router = Router(name="broadcast_plus")

class BPStates(StatesGroup):
    waiting_text = State()
    adding_buttons = State()
    waiting_photo = State()
    confirm = State()

def _admin_only(message: Message) -> bool:
    return message.from_user and message.from_user.id == ADMIN_ID

@router.message(Command("broadcast_plus"))
async def cmd_broadcast_plus(message: Message, state: FSMContext):
    if not _admin_only(message):
        return
    await state.clear()
    await state.update_data(audience="all", parse_mode="HTML", keyboard_layout=[], awaiting_single_btn=False, media=None)
    await message.answer("📣 Введите текст рассылки (HTML разрешён).")
    await state.set_state(BPStates.waiting_text)

@router.message(Command("buyers_broadcast_plus"))
async def cmd_buyers_broadcast_plus(message: Message, state: FSMContext):
    if not _admin_only(message):
        return
    await state.clear()
    await state.update_data(audience="buyers", parse_mode="HTML", keyboard_layout=[], awaiting_single_btn=False, media=None)
    await message.answer("📣 Введите текст рассылки для покупателей (HTML разрешён).")
    await state.set_state(BPStates.waiting_text)

@router.message(BPStates.waiting_text, ~F.text.startswith("/"))
async def got_text(message: Message, state: FSMContext):
    if not _admin_only(message):
        return
    await state.update_data(text=message.html_text or message.text or "")
    kb = _buttons_menu(preview=True, done=True, media=True)
    await message.answer("Добавим кнопки или фото? Можно до 8 URL-кнопок.\nВыберите действие:", reply_markup=kb.as_markup())
    await state.set_state(BPStates.adding_buttons)

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

@router.callback_query(BPStates.adding_buttons, F.data == "btn_add")
async def add_button(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    await callback.message.edit_text("Отправьте кнопку в формате:\n`Текст кнопки | https://example.com`", parse_mode="Markdown")
    data = await state.get_data()
    data["awaiting_single_btn"] = True
    await state.update_data(**data)
    await callback.answer()

# ⛔️ Не перехватываем команды в состоянии добавления кнопок
@router.message(BPStates.adding_buttons, ~F.text.startswith("/"))
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

@router.callback_query(BPStates.adding_buttons, F.data == "btn_rows")
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

@router.callback_query(BPStates.adding_buttons, F.data == "btn_photo")
async def ask_photo(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    await state.set_state(BPStates.waiting_photo)
    await callback.message.answer("Пришлите <b>фото</b> одним сообщением (можно с подписью).", parse_mode="HTML")
    await callback.answer()

@router.message(BPStates.waiting_photo, F.photo)
async def got_photo(message: Message, state: FSMContext):
    if not _admin_only(message):
        return
    file_id = message.photo[-1].file_id
    caption = message.html_text or message.caption or ""
    data = await state.get_data()
    data["media"] = {"type":"photo", "file_id": file_id, "caption": caption, "parse_mode":"HTML"}
    await state.update_data(**data)
    await message.answer("Фото добавлено. Вернусь в конструктор.", reply_markup=_buttons_menu(preview=True, done=True, media=True).as_markup())
    await state.set_state(BPStates.adding_buttons)

@router.callback_query(BPStates.adding_buttons, F.data == "btn_photo_clear")
async def clear_photo(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    data = await state.get_data()
    data["media"] = None
    await state.update_data(**data)
    await callback.message.answer("Фото убрано.", reply_markup=_buttons_menu(preview=True, done=True, media=True).as_markup())
    await callback.answer()

@router.callback_query(BPStates.adding_buttons, F.data == "btn_preview")
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

@router.callback_query(BPStates.adding_buttons, F.data == "btn_done")
async def btn_done(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    await state.set_state(BPStates.confirm)
    data = await state.get_data()
    text = data.get("text","")
    layout = data.get("keyboard_layout", [])
    media = data.get("media")
    kb_prev = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn["text"], url=btn["url"]) for btn in row] for row in layout if row
    ]) if layout else None
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Отправить", callback_data="bp_send")
    kb.button(text="❌ Отмена", callback_data="bp_cancel")
    kb.adjust(2)
    if media and media.get("type") == "photo" and media.get("file_id"):
        await callback.message.answer_photo(media["file_id"], caption=(media.get("caption") or text)[:1024] or "(без подписи)", parse_mode="HTML", reply_markup=kb_prev)
    else:
        await callback.message.answer(text or "(пусто)", reply_markup=kb_prev, disable_web_page_preview=True)
    await callback.message.answer("Подтвердите отправку.", reply_markup=kb.as_markup())
    await callback.answer()

@router.callback_query(BPStates.confirm, F.data == "bp_cancel")
async def bp_cancel(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    await state.clear()
    await callback.message.edit_text("❌ Отправка отменена.")
    await callback.answer()

@router.callback_query(BPStates.confirm, F.data == "bp_send")
async def bp_send(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    data = await state.get_data()
    await state.clear()
    audience = data.get("audience","all")
    text = data.get("text","")
    parse_mode = data.get("parse_mode","HTML")
    layout = data.get("keyboard_layout", [])
    media = data.get("media")
    payload = {"buttons": layout, "media": media} if media else layout
    progress_msg = await callback.message.answer("Начинаю отправку...")

    async def progress(sent, total, ok, failed):
        try:
            await progress_msg.edit_text(f"Прогресс: {sent}/{total} • OK: {ok} • Ошибки: {failed}")
        except Exception:
            pass

    total, ok, failed = await send_broadcast(callback.bot, audience, text, parse_mode, payload, progress_cb=progress)
    try:
        await progress_msg.edit_text(f"Готово. Итого: {total} • OK: {ok} • Ошибки: {failed}")
    except Exception:
        pass
    await callback.answer()
