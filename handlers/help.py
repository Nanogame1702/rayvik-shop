from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_ID

router = Router(name="help")

@router.message(Command("help"))
async def cmd_help(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="🟢 Мгновенная", callback_data="help_quick_broadcast_plus")
    kb.button(text="⏰ По времени", callback_data="help_quick_broadcast_at")
    kb.button(text="🔄 Повторяющиеся", callback_data="help_quick_recurring")
    kb.button(text="🗂 Список задач", callback_data="help_quick_sched_list")
    kb.adjust(2,2)
    text = (
        "<b>Команды бота</b>\n\n"
        "👮 <b>Админ (рассылки)</b>\n"
        "• /broadcast_plus — мгновенная рассылка всем (до 8 кнопок).\n"
        "• /buyers_broadcast_plus — мгновенная рассылка покупателям.\n"
        "• /broadcast_at — отложенная рассылка по дате и времени.\n"
        "• /buyers_broadcast_at — как выше, но только покупателям.\n"
        "• /scheduled_list — список запланированных/активных задач.\n"
        "• /scheduled_cancel &lt;id&gt; — отменить задачу.\n\n"
        "🔄 <b>Повторяющиеся рассылки</b>\n"
        "• /recurring_broadcast — создать автоматическую рассылку.\n"
        "• /recurring_buyers_broadcast — автоматическая для покупателей.\n"
        "• /recurring_list — управление повторяющимися рассылками.\n\n"
        "🔧 <b>Служебные</b>\n"
        "• /id — показать ваш Telegram ID.\n"
        "• /is_admin — проверить права администратора.\n"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=kb.as_markup())

@router.callback_query(lambda c: c.data in {"help_quick_broadcast_plus","help_quick_broadcast_at","help_quick_sched_list","help_quick_recurring"})
async def help_shortcuts(callback):
    if callback.data == "help_quick_broadcast_plus":
        await callback.message.answer("/broadcast_plus")
    elif callback.data == "help_quick_broadcast_at":
        await callback.message.answer("/broadcast_at")
    elif callback.data == "help_quick_recurring":
        await callback.message.answer("/recurring_list")
    else:
        await callback.message.answer("/scheduled_list")
    await callback.answer()
