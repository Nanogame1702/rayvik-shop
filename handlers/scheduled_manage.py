
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_ID
from services import scheduled_repo

router = Router(name="scheduled_manage")

def _admin_only(message: Message) -> bool:
    return message.from_user and message.from_user.id == ADMIN_ID

def _kb_for_task(task_id: int, pending: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="👁 Предпросмотр", callback_data=f"sched_prev_{task_id}")
    if pending:
        b.button(text="❌ Отменить", callback_data=f"sched_cancel_{task_id}")
    b.adjust(2)
    return b.as_markup()

def _fmt_local(utc_iso: str, tz: str = "Europe/Moscow") -> str:
    try:
        dt_utc = datetime.fromisoformat(utc_iso)
        dt_loc = dt_utc.astimezone(ZoneInfo(tz))
        return dt_loc.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return utc_iso

def _short(text: str, n: int = 200) -> str:
    t = (text or "").strip().replace("\n"," ")
    return (t[:n] + "…") if len(t) > n else t

@router.message(Command("scheduled_list"))
async def scheduled_list(message: Message):
    if not _admin_only(message):
        return
    await scheduled_repo.ensure_schema()
    items = await scheduled_repo.list_upcoming(limit=50)
    if not items:
        await message.answer("Пока нет активных задач.")
        return
    for it in items:
        task_id = it["id"]
        when = _fmt_local(it["scheduled_at_utc"], it.get("tz", "Europe/Moscow"))
        status = it["status"]
        audience = it["audience"].upper()
        txt = _short(it["text"] or "")
        pending = status == "pending"
        await message.answer(
            f"#{task_id} • {audience} • {status} • {when} МСК\n{txt}",
            reply_markup=_kb_for_task(task_id, pending=pending)
        )

@router.message(Command("scheduled_cancel"))
async def scheduled_cancel_cmd(message: Message):
    if not _admin_only(message):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Формат: /scheduled_cancel <id>")
        return
    await scheduled_repo.cancel(int(parts[1]))
    await message.answer(f"❌ Задача #{parts[1]} отменена.")

# ВАЖНО: сначала обрабатываем подтверждение, потом общий шаблон.
@router.callback_query(F.data.startswith("sched_cancel_yes_"))
async def sched_cancel_yes(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    try:
        task_id = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer()
        return
    await scheduled_repo.cancel(task_id)
    try:
        await callback.message.edit_text(f"❌ Задача #{task_id} отменена.")
    except Exception:
        await callback.message.answer(f"❌ Задача #{task_id} отменена.")
    await callback.answer("Отменено.")

@router.callback_query(F.data.startswith("sched_cancel_"))
async def sched_cancel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    # если это уже подтверждение — не перехватываем (подстраховка)
    if callback.data.startswith("sched_cancel_yes_"):
        return
    task_id = int(callback.data.split("_")[-1])
    b = InlineKeyboardBuilder()
    b.button(text="Да, отменить", callback_data=f"sched_cancel_yes_{task_id}")
    b.button(text="Нет", callback_data="noop")
    b.adjust(2)
    await callback.message.answer(f"Подтвердите отмену задачи #{task_id}:", reply_markup=b.as_markup())
    await callback.answer()

@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()

@router.callback_query(F.data.startswith("sched_prev_"))
async def sched_prev(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    task_id = int(callback.data.split("_")[-1])
    task = await scheduled_repo.get_by_id(task_id)
    if not task:
        await callback.answer("Задача не найдена.", show_alert=True)
        return
    kb_payload = None
    layout = None
    try:
        parsed = json.loads(task.get("keyboard_json") or "null")
        if isinstance(parsed, list):
            layout = parsed
        elif isinstance(parsed, dict):
            kb_payload = parsed
            layout = parsed.get("buttons")
    except Exception:
        parsed = None
    if not layout:
        markup = None
    else:
        rows = []
        for row in layout:
            btns = []
            for btn in row:
                text = str(btn.get("text",""))[:64]
                url = str(btn.get("url",""))
                if text and url and (url.startswith("http://") or url.startswith("https://")):
                    btns.append(InlineKeyboardButton(text=text, url=url))
            if btns:
                rows.append(btns)
        markup = InlineKeyboardMarkup(inline_keyboard=rows) if rows else None

    media = None
    if isinstance(kb_payload, dict):
        media = kb_payload.get("media")

    caption = task["text"] or ""
    try:
        if media and media.get("type") == "photo" and media.get("file_id"):
            cap = caption[:1024]
            await callback.message.answer_photo(media["file_id"], caption=cap or "(без подписи)", parse_mode=task.get("parse_mode") or "HTML", reply_markup=markup)
        else:
            await callback.message.answer(caption or "(пусто)", parse_mode=task.get("parse_mode") or "HTML", reply_markup=markup, disable_web_page_preview=True)
    except Exception as e:
        await callback.message.answer(f"Предпросмотр не удался: {e!s}")
    await callback.answer()
