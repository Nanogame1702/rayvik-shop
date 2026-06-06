"""
Обработчик управления повторяющимися рассылками
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_ID
from database import (
    list_recurring_broadcasts,
    get_recurring_broadcast,
    update_recurring_broadcast_status,
    delete_recurring_broadcast,
    get_recurring_send_history,
    get_recurring_stats
)
from services.recurring_service import RecurringBroadcastService

router = Router(name="recurring_manage")


def _admin_only(message: Message) -> bool:
    return message.from_user and message.from_user.id == ADMIN_ID


def _fmt_local(utc_iso: str, tz: str = "Europe/Moscow") -> str:
    """Форматирование времени в локальный часовой пояс"""
    try:
        dt_utc = datetime.fromisoformat(utc_iso)
        dt_loc = dt_utc.astimezone(ZoneInfo(tz))
        return dt_loc.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return utc_iso or "—"


def _short(text: str, n: int = 100) -> str:
    """Сокращение текста"""
    t = (text or "").strip().replace("\n", " ")
    return (t[:n] + "…") if len(t) > n else t


def _kb_for_recurring(recurring_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Клавиатура для управления рассылкой"""
    b = InlineKeyboardBuilder()
    b.button(text="👁 Просмотр", callback_data=f"rec_view_{recurring_id}")
    
    if is_active:
        b.button(text="⏸ Пауза", callback_data=f"rec_pause_{recurring_id}")
    else:
        b.button(text="▶️ Возобновить", callback_data=f"rec_resume_{recurring_id}")
    
    b.button(text="📊 Статистика", callback_data=f"rec_stats_{recurring_id}")
    b.button(text="🗑 Удалить", callback_data=f"rec_delete_{recurring_id}")
    b.adjust(2, 2)
    return b.as_markup()


# ============================================================================
# СПИСОК РАССЫЛОК
# ============================================================================

@router.message(Command("recurring_list"))
async def recurring_list(message: Message):
    """Список всех повторяющихся рассылок"""
    if not _admin_only(message):
        return
    
    items = await list_recurring_broadcasts()
    
    if not items:
        await message.answer("📭 Пока нет повторяющихся рассылок.\n\nИспользуйте /recurring_broadcast для создания.")
        return
    
    await message.answer(f"📋 <b>Повторяющиеся рассылки ({len(items)})</b>", parse_mode="HTML")
    
    for item in items:
        recurring_id = item["id"]
        name = item["name"]
        is_active = bool(item["is_active"])
        status_emoji = "🟢" if is_active else "🔴"
        status_text = "активна" if is_active else "приостановлена"
        
        # Формируем описание расписания
        pattern = item["schedule_pattern"]
        time = item["schedule_time"]
        
        if pattern == "daily":
            schedule = f"Каждый день в {time}"
        elif pattern == "weekly":
            days_json = item["schedule_days"] if "schedule_days" in item.keys() else "[]"
            days = json.loads(days_json or "[]")
            day_names = {1: 'Пн', 2: 'Вт', 3: 'Ср', 4: 'Чт', 5: 'Пт', 6: 'Сб', 7: 'Вс'}
            days_str = ', '.join(day_names.get(d, str(d)) for d in sorted(days))
            schedule = f"Каждую неделю: {days_str} в {time}"
        else:  # monthly
            day = item["schedule_day_of_month"] if "schedule_day_of_month" in item.keys() else 1
            schedule = f"Каждый месяц {day} числа в {time}"
        
        audience = "Все" if item["audience"] == "all" else "Покупатели"
        total_sends = item["total_sends"]
        tz = item["timezone"] if "timezone" in item.keys() else "Europe/Moscow"
        last_sent = _fmt_local(item["last_sent_at"] if "last_sent_at" in item.keys() else None, tz)
        next_send = _fmt_local(item["next_send_at"] if "next_send_at" in item.keys() else None, tz)
        
        text_preview = _short(item["text"], 80)
        
        msg_text = (
            f"#{recurring_id} {status_emoji} <b>{name}</b> ({status_text})\n"
            f"📅 {schedule} МСК\n"
            f"👥 Аудитория: {audience}\n"
            f"📊 Отправлено: {total_sends} раз\n"
        )
        
        if is_active and next_send != "—":
            msg_text += f"⏰ Следующая: {next_send} МСК\n"
        elif last_sent != "—":
            msg_text += f"⏰ Последняя: {last_sent} МСК\n"
        
        msg_text += f"\n💬 {text_preview}"
        
        await message.answer(
            msg_text,
            reply_markup=_kb_for_recurring(recurring_id, is_active),
            parse_mode="HTML"
        )


# ============================================================================
# ПРОСМОТР РАССЫЛКИ
# ============================================================================

@router.callback_query(F.data.startswith("rec_view_"))
async def rec_view(callback: CallbackQuery):
    """Предпросмотр рассылки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    recurring_id = int(callback.data.split("_")[-1])
    recurring = await get_recurring_broadcast(recurring_id)
    
    if not recurring:
        await callback.answer("❌ Рассылка не найдена", show_alert=True)
        return
    
    # Парсим keyboard_json
    try:
        kb_json = recurring["keyboard_json"] if "keyboard_json" in recurring.keys() else "[]"
        keyboard_data = json.loads(kb_json or "[]")
        
        if isinstance(keyboard_data, dict):
            layout = keyboard_data.get("buttons", [])
            media = keyboard_data.get("media")
        else:
            layout = keyboard_data
            media = None
        
        # Создаем клавиатуру
        kb = None
        if layout:
            rows = []
            for row in layout:
                btns = []
                for btn in row:
                    text = str(btn.get("text", ""))[:64]
                    url = str(btn.get("url", ""))
                    if text and url and (url.startswith("http://") or url.startswith("https://")):
                        btns.append(InlineKeyboardButton(text=text, url=url))
                if btns:
                    rows.append(btns)
            if rows:
                kb = InlineKeyboardMarkup(inline_keyboard=rows)
        
        # Отправляем предпросмотр
        text = recurring["text"] or "(пусто)"
        parse_mode = recurring["parse_mode"] if "parse_mode" in recurring.keys() else "HTML"
        
        if media and media.get("type") == "photo" and media.get("file_id"):
            caption = (media.get("caption") or text)[:1024]
            await callback.message.answer_photo(
                media["file_id"],
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=kb
            )
        else:
            await callback.message.answer(
                text,
                parse_mode=parse_mode,
                reply_markup=kb,
                disable_web_page_preview=True
            )
        
        await callback.answer("👁 Предпросмотр отправлен")
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка предпросмотра: {e}")
        await callback.answer()


# ============================================================================
# ПАУЗА / ВОЗОБНОВЛЕНИЕ
# ============================================================================

@router.callback_query(F.data.startswith("rec_pause_"))
async def rec_pause(callback: CallbackQuery):
    """Приостановка рассылки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    recurring_id = int(callback.data.split("_")[-1])
    
    try:
        await update_recurring_broadcast_status(recurring_id, is_active=False)
        await callback.message.edit_text(
            f"⏸ Рассылка #{recurring_id} приостановлена.\n\n"
            "Используйте /recurring_list для управления.",
            parse_mode="HTML"
        )
        await callback.answer("✅ Приостановлено")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.callback_query(F.data.startswith("rec_resume_"))
async def rec_resume(callback: CallbackQuery):
    """Возобновление рассылки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    recurring_id = int(callback.data.split("_")[-1])
    
    try:
        await update_recurring_broadcast_status(recurring_id, is_active=True)
        
        # Создаем задачу если её нет
        task_id = await RecurringBroadcastService.create_scheduled_task_from_recurring(recurring_id)
        
        if task_id:
            await callback.message.edit_text(
                f"▶️ Рассылка #{recurring_id} возобновлена.\n"
                f"Создана задача #{task_id}\n\n"
                "Используйте /recurring_list для управления.",
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                f"⚠️ Рассылка #{recurring_id} возобновлена, но не удалось создать задачу.\n\n"
                "Проверьте логи.",
                parse_mode="HTML"
            )
        
        await callback.answer("✅ Возобновлено")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)



# ============================================================================
# СТАТИСТИКА
# ============================================================================

@router.callback_query(F.data.startswith("rec_stats_"))
async def rec_stats(callback: CallbackQuery):
    """Статистика рассылки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    recurring_id = int(callback.data.split("_")[-1])
    
    try:
        recurring = await get_recurring_broadcast(recurring_id)
        if not recurring:
            await callback.answer("❌ Рассылка не найдена", show_alert=True)
            return
        
        stats = await get_recurring_stats(recurring_id)
        history = await get_recurring_send_history(recurring_id, limit=5)
        
        # Формируем сообщение
        msg = f"📊 <b>Статистика рассылки #{recurring_id}</b>\n\n"
        msg += f"📝 Название: <b>{recurring['name']}</b>\n\n"
        
        if stats:
            total = stats["total_sends"] or 0
            success = stats["successful_sends"] or 0
            failed = stats["failed_sends"] or 0
            recipients = stats["total_recipients"] or 0
            
            msg += f"📤 Всего отправок: {total}\n"
            msg += f"✅ Успешных: {success}\n"
            msg += f"❌ Ошибок: {failed}\n"
            msg += f"👥 Всего получателей: {recipients:,}\n\n"
        else:
            msg += "📤 Отправок пока не было\n\n"
        
        tz = recurring["timezone"] if "timezone" in recurring.keys() else "Europe/Moscow"
        created_at = _fmt_local(recurring["created_at"] if "created_at" in recurring.keys() else None, tz)
        last_sent = _fmt_local(recurring["last_sent_at"] if "last_sent_at" in recurring.keys() else None, tz)
        next_send = _fmt_local(recurring["next_send_at"] if "next_send_at" in recurring.keys() else None, tz)
        
        msg += f"📅 Создана: {created_at}\n"
        if last_sent != "—":
            msg += f"⏰ Последняя: {last_sent}\n"
        if next_send != "—" and recurring["is_active"]:
            msg += f"⏰ Следующая: {next_send}\n"
        
        # История последних отправок
        if history:
            msg += f"\n📈 <b>История (последние {len(history)})</b>:\n"
            for log in history:
                status_emoji = "✅" if log["status"] == "success" else "❌"
                log_sent_at = log["sent_at"] if "sent_at" in log.keys() else None
                sent_at = _fmt_local(log_sent_at, tz)
                recipients_count = log["recipients_count"] if "recipients_count" in log.keys() else 0
                
                msg += f"{status_emoji} {sent_at}"
                if log["status"] == "success":
                    msg += f" — {recipients_count:,} получателей\n"
                else:
                    error = log["error_message"] if "error_message" in log.keys() else "неизвестная ошибка"
                    msg += f" — {error[:50]}\n"
        
        await callback.message.answer(msg, parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка получения статистики: {e}")
        await callback.answer()


# ============================================================================
# УДАЛЕНИЕ
# ============================================================================

@router.callback_query(F.data.startswith("rec_delete_yes_"))
async def rec_delete_confirm(callback: CallbackQuery):
    """Подтверждение удаления (ВАЖНО: должен быть ПЕРЕД rec_delete_)"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    recurring_id = int(callback.data.split("_")[-1])
    
    try:
        await delete_recurring_broadcast(recurring_id)
        await callback.message.edit_text(
            f"🗑 Рассылка #{recurring_id} удалена.\n\n"
            "Используйте /recurring_list для просмотра оставшихся.",
            parse_mode="HTML"
        )
        await callback.answer("✅ Удалено")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.callback_query(F.data.startswith("rec_delete_"))
async def rec_delete(callback: CallbackQuery):
    """Запрос подтверждения удаления (ВАЖНО: должен быть ПОСЛЕ rec_delete_confirm_)"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    recurring_id = int(callback.data.split("_")[-1])
    
    # Показываем подтверждение
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, удалить", callback_data=f"rec_delete_yes_{recurring_id}")
    kb.button(text="❌ Отмена", callback_data="rec_delete_cancel")
    kb.adjust(2)
    
    await callback.message.answer(
        f"⚠️ <b>Подтвердите удаление рассылки #{recurring_id}</b>\n\n"
        "Это действие нельзя отменить. Будут удалены:\n"
        "• Шаблон рассылки\n"
        "• Вся история отправок\n"
        "• Запланированные задачи",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "rec_delete_cancel")
async def rec_delete_cancel(callback: CallbackQuery):
    """Отмена удаления"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    await callback.message.edit_text("❌ Удаление отменено.")
    await callback.answer()
