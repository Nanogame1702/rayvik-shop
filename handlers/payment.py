from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import create_order, update_order_photo, update_order_status, get_order
from keyboards import get_payment_methods, get_payment_confirmation, get_back_button, get_admin_decision
from config import EMOJI, PAYMENT_CARD, PAYMENT_YOOMONEY, PAYMENT_SBP_PHONE, PAYMENT_SBP_NAME, PAYMENT_SBP_BANK, ADMIN_ID
from handlers.catalog import PRODUCTS

router = Router()

class PaymentStates(StatesGroup):
    waiting_for_photo = State()

@router.callback_query(F.data.startswith("pay_"))
async def process_payment_method(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    payment_method = parts[1]
    product_id = "_".join(parts[2:])
    
    if product_id not in PRODUCTS:
        await callback.answer("Товар не найден!", show_alert=True)
        return
    
    product = PRODUCTS[product_id]
    data = await state.get_data()
    promo_discount = data.get('promo_discount', 0)
    final_price = int(product["price"] * (1 - promo_discount / 100))
    
    order_id = await create_order(
        user_id=callback.from_user.id,
        product_id=product_id,
        product_name=product["name"],
        product_price=final_price,
        payment_method=payment_method
    )
    
    if payment_method == "card":
        payment_details = f"{EMOJI['card']} **Банковская карта**\n`{PAYMENT_CARD}`"
    elif payment_method == "yoomoney":
        payment_details = f"{EMOJI['money']} **ЮMoney**\n`{PAYMENT_YOOMONEY}`"
    elif payment_method == "sbp":
        payment_details = (
            f"{EMOJI['wind']} **СБП (без комиссии)**\n"
            f"Телефон: `{PAYMENT_SBP_PHONE}`\n"
            f"Получатель: {PAYMENT_SBP_NAME}\n"
            f"Банк: {PAYMENT_SBP_BANK}"
        )
    else:
        payment_details = "Неизвестный метод оплаты"
    
    text = (
        f"{EMOJI['package']} **{product['name']}**\n"
        f"{EMOJI['money']} Сумма: **{final_price}₽**\n\n"
        f"{payment_details}\n\n"
        f"{EMOJI['alert']} Отправьте скриншот чека после оплаты!"
    )
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_back_button())
    await state.update_data(order_id=order_id)
    await state.set_state(PaymentStates.waiting_for_photo)
    await callback.answer()

@router.message(PaymentStates.waiting_for_photo, F.photo)
async def handle_payment_photo(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    order_id = data.get("order_id")
    
    if not order_id:
        await message.answer("Ошибка: заказ не найден.")
        await state.clear()
        return
    
    photo_id = message.photo[-1].file_id
    await update_order_photo(order_id, photo_id)
    
    order = await get_order(order_id)
    
    admin_text = (
        f"{EMOJI['alert']} **Новый заказ #{order_id}**\n\n"
        f"{EMOJI['package']} Товар: **{order['product_name']}**\n"
        f"{EMOJI['money']} Сумма: **{order['product_price']}₽**\n"
        f"{EMOJI['card']} Способ: {order['payment_method']}\n"
        f"👤 Пользователь: {message.from_user.mention_html()}"
    )
    
    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_id,
        caption=admin_text,
        parse_mode="HTML",
        reply_markup=get_admin_decision(order_id)
    )
    
    await message.answer(
        f"{EMOJI['check']} Чек получен!\n\n"
        f"Ожидайте подтверждения от администратора."
    )
    await state.clear()

@router.callback_query(F.data.startswith("confirm_payment_"))
async def confirm_payment(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[2])
    await state.set_state(PaymentStates.waiting_for_photo)
    await state.update_data(order_id=order_id)
    
    text = f"{EMOJI['check']} **ПОДТВЕРЖДЕНИЕ ОПЛАТЫ**\n\n"
    text += f"{EMOJI['plane']} Отправьте **фото чека** или скриншот перевода\n\n"
    text += f"📸 **Требования:**\n"
    text += f"• Чек четкий и читаемый\n"
    text += f"• Видна сумма и дата\n"
    text += f"• Желательно скриншот из банка\n\n"
    text += f"{EMOJI['lightning']} После проверки (1-60мин, возможно задержки!) вы получите товар!"
    
    # ВАЖНО: Удаляем старое сообщение и отправляем новое
    await callback.message.delete()
    await callback.message.answer(
        text,
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("cancel_order_"))
async def cancel_order(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    await update_order_status(order_id, "cancelled")
    await callback.message.edit_text(
        f"{EMOJI['cross']} Заказ отменён.\n\nВы можете выбрать другой товар.",
        reply_markup=get_back_button()
    )
    await callback.answer()

@router.callback_query(F.data == "back_from_payment")
async def back_from_payment(callback: CallbackQuery):
    from keyboards import get_main_menu
    await callback.message.edit_text(
        f"{EMOJI['fire']} **Добро пожаловать в RAYVIK SHOP!**\n\n"
        f"Выберите категорию:",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )
    await callback.answer()
