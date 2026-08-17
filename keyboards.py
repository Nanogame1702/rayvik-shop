from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import EMOJI

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{EMOJI['fire']} Приватные моды", callback_data="category_cheats")],
        [InlineKeyboardButton(text=f"{EMOJI['diamond']} Алмазы Free Fire", callback_data="category_diamonds")]
    ])

def get_cheats_category():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ВХ + АИМБОТ - 150₽", callback_data="product_cheat_1")],
        [InlineKeyboardButton(text="ПОЛНЫЙ МОД - 300₽", callback_data="product_cheat_2")],
        [InlineKeyboardButton(text="PREMIUM + СКИНЫ - 500₽", callback_data="product_cheat_3")],
        [InlineKeyboardButton(text=f"{EMOJI['back']} Назад", callback_data="back_to_main")]
    ])

def get_diamonds_category():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 5000 АЛМАЗОВ - 199₽", callback_data="product_diamonds_1")],
        [InlineKeyboardButton(text="💎 10000 АЛМАЗОВ - 349₽", callback_data="product_diamonds_2")],
        [InlineKeyboardButton(text="💎 30000 АЛМАЗОВ - 599₽", callback_data="product_diamonds_3")],
        [InlineKeyboardButton(text=f"{EMOJI['back']} Назад", callback_data="back_to_main")]
    ])

def get_payment_methods(product_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{EMOJI['card']} Банковская карта", callback_data=f"pay_card_{product_id}")],
        [InlineKeyboardButton(text=f"{EMOJI['money']} ЮMoney", callback_data=f"pay_yoomoney_{product_id}")],
        [InlineKeyboardButton(text=f"{EMOJI['wind']} СБП (без комиссии)", callback_data=f"pay_sbp_{product_id}")],
        [InlineKeyboardButton(text=f"{EMOJI['back']} Назад", callback_data="back_from_payment")]
    ])

def get_payment_confirmation(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{EMOJI['check']} Оплатил", callback_data=f"confirm_payment_{order_id}")],
        [InlineKeyboardButton(text=f"{EMOJI['cross']} Отменить", callback_data=f"cancel_order_{order_id}")]
    ])

def get_back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{EMOJI['back']} В главное меню", callback_data="back_to_main")]
    ])

def get_admin_decision(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{EMOJI['check']} Принять", callback_data=f"admin_accept_{order_id}"),
            InlineKeyboardButton(text=f"{EMOJI['cross']} Отклонить", callback_data=f"admin_reject_{order_id}"),
            InlineKeyboardButton(text="💸 Возврат", callback_data=f"admin_refund_{order_id}")
        ]
    ])
