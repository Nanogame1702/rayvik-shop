from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import get_promocode, use_promocode
from handlers.catalog import PromoStates, PRODUCTS
from keyboards import get_payment_methods
from config import EMOJI

router = Router()

@router.message(PromoStates.waiting_for_promo)
async def process_promo_code(message: Message, state: FSMContext):
    promo_code = message.text.strip().upper()
    data = await state.get_data()
    
    product_id = data.get('product_id')
    base_price = data.get('base_price')
    
    if not product_id or not base_price:
        await message.answer(f"{EMOJI['cross']} Ошибка! Начните заново.")
        await state.clear()
        return
    
    promo = await get_promocode(promo_code)
    
    if not promo:
        await message.answer(f"{EMOJI['cross']} **Промокод не найден!**\n\nПроверьте правильность ввода.", parse_mode="Markdown")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJI['berry']} Попробовать снова", callback_data=f"enter_promo_{product_id}")],
            [InlineKeyboardButton(text=f"{EMOJI['arrow']} Продолжить без промокода", callback_data=f"skip_promo_{product_id}")]
        ])
        await message.answer("Что дальше?", reply_markup=keyboard)
        await state.set_state(None)
        return
    
    if promo['max_uses'] > 0 and promo['current_uses'] >= promo['max_uses']:
        await message.answer(f"{EMOJI['cross']} **Промокод исчерпан!**", parse_mode="Markdown")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJI['arrow']} Продолжить без промокода", callback_data=f"skip_promo_{product_id}")]
        ])
        await message.answer("Продолжить?", reply_markup=keyboard)
        await state.set_state(None)
        return
    
    discount = promo['discount']
    final_price = int(base_price * (100 - discount) / 100)
    
    await state.update_data(final_price=final_price, promo_code=promo_code, discount=discount)
    await use_promocode(promo_code)
    
    product = PRODUCTS[product_id]
    
    text = f"{EMOJI['check']} **ПРОМОКОД ПРИМЕНЁН!**\n\n"
    text += f"🎫 Промокод: `{promo_code}`\n"
    text += f"📝 {promo['description']}\n\n"
    text += f"💰 Базовая цена: ~~{base_price}₽~~\n"
    text += f"🔥 Скидка: **-{discount}%**\n"
    text += f"✨ Итого: **{final_price}₽**\n\n"
    text += f"_{EMOJI['lightning']} Экономия {base_price - final_price}₽!_"
    
    await message.answer(text, parse_mode="Markdown")
    await message.answer(f"{EMOJI['arrow']} **Выберите способ оплаты:**", reply_markup=get_payment_methods(product_id), parse_mode="Markdown")
    
    await state.set_state(None)
