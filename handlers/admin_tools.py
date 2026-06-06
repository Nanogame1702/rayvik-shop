from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from config import ADMIN_ID

router = Router(name="admin_tools")

@router.message(Command("id"))
async def cmd_id(m: Message):
    await m.answer(f"Ваш ID: <code>{m.from_user.id}</code>\nADMIN_ID: <code>{ADMIN_ID}</code>", parse_mode="HTML")

@router.message(Command("is_admin"))
async def cmd_is_admin(m: Message):
    ok = (m.from_user and m.from_user.id == ADMIN_ID)
    await m.answer("is_admin = " + ("✅" if ok else "❌"))
