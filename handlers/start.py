from pathlib import Path

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo,
    InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
)
from aiogram.fsm.context import FSMContext

from database import add_user
from config import EMOJI

router = Router()

# ВСТАВЬТЕ СЮДА ВАШУ ССЫЛКУ С VERCEL!
WEBAPP_URL = "https://main-five-sage.vercel.app/"
START_IMAGE_PATH = Path('assets') / 'luno pc and apple.png'

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🛍 Открыть магазин",
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )
            ]
        ],
        resize_keyboard=True
    )
    
    welcome_text = ("💎 Добро пожаловать в RAYVIK SHOP!\n\n🔥 Нажмите кнопку 'Открыть магазин' ниже\n⚡️ Все покупки через Mini App!")

    if START_IMAGE_PATH.exists():
        await message.answer_photo(
            photo=FSInputFile(START_IMAGE_PATH),
            caption=welcome_text,
            reply_markup=keyboard
        )
    else:
        await message.answer(welcome_text, reply_markup=keyboard)


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = "🔥 Используйте кнопку ниже для открытия магазина"
    try:
        await callback.message.edit_text(text)
    except:
        await callback.message.answer(text)
    await callback.answer()
