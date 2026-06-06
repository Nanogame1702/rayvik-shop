from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from keyboards import get_cheats_category, get_diamonds_category, get_payment_methods, get_main_menu
from config import EMOJI

router = Router()

CHEAT_PHOTO = "photo_2025-10-02_00-49-38.jpg"
DIAMONDS_PHOTO = "photo_2025-10-02_00-49-55.jpg"

class PromoStates(StatesGroup):
    waiting_for_promo = State()

PRODUCTS = {
    'cheat_1': {
        'name': 'ВХ ЧЕРЕЗ СТЕНЫ + АИМБОТ',
        'price': 150,
        'description': f"{EMOJI['fire']} Приватный мод Free Fire\n{EMOJI['alert']} Не требует Root\n{EMOJI['lightning']} Быстрые обновления\n{EMOJI['lock']} Защита от бана"
    },
    'cheat_2': {
        'name': 'ПОЛНЫЙ ФУНКЦИОНАЛ + МЕНЮ',
        'price': 300,
        'description': f"{EMOJI['diamond']} Все читы в одном\n{EMOJI['lock']} Максимальная безопасность\n{EMOJI['lightning']} Поддержка 24/7\n{EMOJI['fire']} Регулярные обновления"
    },
    'cheat_3': {
        'name': 'PREMIUM MOD + ВСЕ СКИНЫ',
        'price': 500,
        'description': f"{EMOJI['star']} Все возможности\n{EMOJI['diamond']} Бесплатные скины\n{EMOJI['fire']} VIP функции\n{EMOJI['heart']} Полная поддержка"
    },
    'diamonds_1': {
        'name': '500 АЛМАЗОВ',
        'price': 150,
        'description': f"{EMOJI['diamond']} 500 алмазов на аккаунт\n{EMOJI['lightning']} Моментальная доставка\n{EMOJI['check']} Безопасно и надёжно"
    },
    'diamonds_2': {
        'name': '1000 АЛМАЗОВ',
        'price': 250,
        'description': f"{EMOJI['diamond']} 1000 алмазов на аккаунт\n{EMOJI['lightning']} Моментальная доставка\n{EMOJI['fire']} Популярный выбор"
    },
    'diamonds_3': {
        'name': '3000 АЛМАЗОВ',
        'price': 399,
        'description': f"{EMOJI['diamond']} 3000 алмазов на аккаунт\n{EMOJI['star']} Выгодное предложение\n{EMOJI['lightning']} Моментальная доставка\n{EMOJI['alert']} Лучшая цена"
    }
}

@router.callback_query(F.data == "category_cheats")
async def show_cheats(callback: CallbackQuery):
    text = f"{EMOJI['fire']} **ПРИВАТНЫЕ МОДЫ**\nВыберите товар:"
    photo = FSInputFile(CHEAT_PHOTO)
    await callback.message.delete()
    await callback.message.answer_photo(photo=photo, caption=text, reply_markup=get_cheats_category(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "category_diamonds")
async def show_diamonds(callback: CallbackQuery):
    text = f"{EMOJI['diamond']} **АЛМАЗЫ FREE FIRE**\n{EMOJI['lightning']} Быстрая доставка!\nВыберите количество:"
    photo = FSInputFile(DIAMONDS_PHOTO)
    await callback.message.delete()
    await callback.message.answer_photo(photo=photo, caption=text, reply_markup=get_diamonds_category(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("product_"))
async def show_product(callback: CallbackQuery, state: FSMContext):
    product_id = callback.data.replace("product_", "")
    
    if product_id in PRODUCTS:
        product = PRODUCTS[product_id]
        await state.update_data(product_id=product_id, base_price=product['price'], final_price=product['price'], promo_code=None)
        
        text = f"{EMOJI['package']} **{product['name']}**\n\n{product['description']}\n\n{EMOJI['star']} У вас есть промокод?"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJI['berry']} Ввести промокод", callback_data=f"enter_promo_{product_id}")],
            [InlineKeyboardButton(text=f"{EMOJI['arrow']} Перейти к оплате", callback_data=f"skip_promo_{product_id}")],
            [InlineKeyboardButton(text=f"{EMOJI['back']} Назад", callback_data="back_from_payment")]
        ])
        
        await callback.message.edit_caption(caption=text, reply_markup=keyboard, parse_mode="Markdown")
    
    await callback.answer()

@router.callback_query(F.data.startswith("enter_promo_"))
async def enter_promo_code(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PromoStates.waiting_for_promo)
    text = f"{EMOJI['berry']} **ВВОД ПРОМОКОДА**\n\nОтправьте промокод в чат"
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("skip_promo_"))
async def skip_promo(callback: CallbackQuery):
    product_id = callback.data.replace("skip_promo_", "")
    text = f"{EMOJI['arrow']} **Выберите способ оплаты:**"
    
    try:
        await callback.message.edit_caption(caption=text, reply_markup=get_payment_methods(product_id), parse_mode="Markdown")
    except:
        try:
            await callback.message.edit_text(text, reply_markup=get_payment_methods(product_id), parse_mode="Markdown")
        except:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=get_payment_methods(product_id), parse_mode="Markdown")
    
    await callback.answer()

@router.callback_query(F.data == "back_from_payment")
async def back_from_payment(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    
    text = f"{EMOJI['fire']} **RAYVIK SHOP**\n\nВыберите категорию:"
    await callback.message.answer(text, reply_markup=get_main_menu(), parse_mode="Markdown")
    await callback.answer()
