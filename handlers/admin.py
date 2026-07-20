from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery, Message,
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest, TelegramNotFound
import aiosqlite

from database import update_order_status, get_order, add_promocode, delete_promocode, get_all_promocodes, toggle_promocode, get_buyer_user_ids, get_existing_user_ids
from config import EMOJI, ADMIN_ID

router = Router()

class BuyersBroadcastStates(StatesGroup):
    waiting_for_message = State()

WEBAPP_URL = "https://main-five-sage.vercel.app"

class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirmation = State()

class PromoAdminStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_discount = State()
    waiting_for_description = State()
    waiting_for_max_uses = State()

def get_webapp_keyboard():
    """Клавиатура с кнопкой веб-приложения"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"{EMOJI['fire']} Открыть магазин", web_app=WebAppInfo(url=WEBAPP_URL))]
        ],
        resize_keyboard=True
    )

# ============ ОБРАБОТКА ЗАКАЗОВ ============

@router.callback_query(F.data.startswith("admin_accept_"))
async def admin_accept_order(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет прав!", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[2])
    order = await get_order(order_id)
    
    if not order:
        await callback.answer("Заказ не найден!", show_alert=True)
        return
    
    await update_order_status(order_id, "completed")
    
    # Проверяем, является ли товар читом (а не алмазами)
    is_cheat = any(keyword in order['product_name'].upper() for keyword in 
                   ['ЧИТ', 'МОД', 'АИМБОТ', 'ВХ', 'МЕНЮ', 'ФУНКЦИОНАЛ', 'PREMIUM', 'СКИН', 'СКИНЫ', 'ПОЛНЫЙ'])
    
    if is_cheat:
        # Отправляем сообщение + ZIP файл для читов
        user_text = (
            f"🎉 **ПОЗДРАВЛЯЕМ С ПОКУПКОЙ!**\n\n"
            f"✅ Оплата успешно подтверждена!\n\n"
            f"📦 **Товар:** {order['product_name']}\n"
            f"💰 **Сумма:** {order['product_price']}₽\n\n"
            f"📥 **Ваш чит готов к установке!**\n"
            f"⬇️ Файл отправлен ниже\n\n"
            f"📱 **Инструкция:**\n"
            f"1. Скачайте ZIP архив\n"
            f"2. Распакуйте архив (пароль будет указан)\n"
            f"3. Установите файлы согласно инструкции внутри\n"
            f"4. Запустите игру через мод\n\n"
            f"⚠️ **Важно:** Не обновляйте игру без обновления мода!\n\n"
            f"💬 Возникли вопросы? Напишите в поддержку\n"
            f"💎 Спасибо за покупку в **RAYVIK SHOP**!"
        )
        
        # Отправляем текст
        await bot.send_message(order["user_id"], user_text, parse_mode="Markdown")
        
        # Отправляем чит-файл
        try:
            from aiogram.types import FSInputFile
            import os
            import aiohttp
            
            # Путь к ZIP файлу
            cheat_file_path = "files/MACRO.zip"
            
            # Если файл не существует локально, скачиваем с Google Drive
            if not os.path.exists(cheat_file_path):
                # ID файла с Google Drive
                google_drive_file_id = "1WGmIV42pOgMGr2k8y8cYrj2TPCsH894x"
                download_url = f"https://drive.google.com/uc?export=download&id={google_drive_file_id}"
                
                os.makedirs("files", exist_ok=True)
                
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(download_url) as resp:
                            if resp.status == 200:
                                with open(cheat_file_path, 'wb') as f:
                                    f.write(await resp.read())
                except Exception as e:
                    await bot.send_message(
                        ADMIN_ID,
                        f"⚠️ Ошибка скачивания файла с Google Drive для заказа #{order_id}: {e}"
                    )
            
            # Проверяем, существует ли файл после скачивания
            if os.path.exists(cheat_file_path):
                cheat_file = FSInputFile(cheat_file_path)
                
                # Отправляем файл с подробной инструкцией
                await bot.send_document(
                    order["user_id"],
                    document=cheat_file,
                    caption=(
                        f"🔥 **{order['product_name']}**\n\n"
                        f"✅ Версия: v5.0\n"
                        f"🛡 Защита от бана: Активна\n\n"
                        f"🔐 **ПАРОЛЬ ОТ АРХИВА:**\n"
                        f"`134578`\n\n"
                        f"💡 Скопируйте пароль для распаковки"
                    ),
                    parse_mode="Markdown"
                )
            else:
                # Если файл всё равно не найден
                await bot.send_message(
                    order["user_id"],
                    "⚠️ Файл временно недоступен. Администратор отправит его вручную в течение 5 минут!",
                    parse_mode="Markdown"
                )
                await bot.send_message(
                    ADMIN_ID,
                    f"⚠️ Файл не найден и не скачан для заказа #{order_id}\n"
                    f"Отправь ZIP файл вручную пользователю: {order['user_id']}"
                )
                
        except Exception as e:
            # В случае ошибки уведомляем админа
            await bot.send_message(
                ADMIN_ID,
                f"⚠️ Ошибка отправки файла для заказа #{order_id}: {e}\n"
                f"Отправь ZIP файл вручную пользователю: {order['user_id']}"
            )
    else:
        # Для алмазов — стандартное сообщение
        user_text = (
            f"{EMOJI['check']} **Оплата успешно подтверждена!**\n\n"
            f"{EMOJI['package']} **Товар:** {order['product_name']}\n"
            f"{EMOJI['money']} **Сумма:** {order['product_price']}₽\n\n"
            f"{EMOJI['lightning']} Алмазы будут зачислены в течение **15 минут**!\n"
            f"{EMOJI['heart']} Спасибо за покупку в **RAYVIK SHOP**!"
        )
        await bot.send_message(order["user_id"], user_text, parse_mode="Markdown")
    
    try:
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n✅ **Заказ принят администратором**",
            parse_mode="Markdown"
        )
    except:
        pass
    
    await callback.answer(f"{EMOJI['check']} Заказ #{order_id} принят!")

@router.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject_order(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет прав!", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[2])
    order = await get_order(order_id)
    
    if not order:
        await callback.answer("Заказ не найден!", show_alert=True)
        return
    
    await update_order_status(order_id, "rejected")
    
    user_text = (
        f"{EMOJI['cross']} **Оплата отклонена**\n\n"
        f"{EMOJI['package']} **Товар:** {order['product_name']}\n"
        f"{EMOJI['money']} **Сумма:** {order['product_price']}₽\n\n"
        f"{EMOJI['alert']} **Возможные причины:**\n"
        "• Неверная сумма платежа\n"
        "• Нечитаемый или некорректный чек\n"
        "• Платёж не найден в системе\n\n"
        f"{EMOJI['lightning']} Проверьте данные и попробуйте оформить заказ снова."
    )
    
    await bot.send_message(order["user_id"], user_text, parse_mode="Markdown", reply_markup=get_webapp_keyboard())
    
    try:
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n❌ **Заказ отклонён администратором**",
            parse_mode="Markdown"
        )
    except:
        pass
    
    await callback.answer(f"{EMOJI['cross']} Заказ #{order_id} отклонён!")

@router.callback_query(F.data.startswith("admin_refund_"))
async def admin_refund_order(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет прав!", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[2])
    order = await get_order(order_id)
    
    if not order:
        await callback.answer("Заказ не найден!", show_alert=True)
        return
    
    await update_order_status(order_id, "refunded")
    
    user_text = (
        f"❗ **Искренне приносим извинения за доставленные неудобства**\n\n"
        f"{EMOJI['alert']} По заказу **#{order_id}** ({order['product_name']}) обнаружена ошибка в платёжных реквизитах.\n\n"
        f"{EMOJI['money']} **Возврат средств инициирован**\n"
        f"{EMOJI['clock']} Срок возврата: до 3-х рабочих дней\n"
        f"{EMOJI['alert']} Точное время зачисления зависит от вашего банка\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"{EMOJI['berry']} **В качестве компенсации** мы дарим вам промокод:\n"
        f"**`REF20`** — скидка **20%** на следующий заказ!\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"{EMOJI['fire']} Чтобы получить товар по **обновлённым реквизитам** и с промокодом, оформите заказ повторно через наш магазин.\n\n"
        f"{EMOJI['heart']} Благодарим за понимание, ОПЛАТИТЬ НУЖНО ДО КОНЦА ЭТОГО ДНЯ, акция закончится и цена вырастет на 60%!"
    )
    
    await bot.send_message(order["user_id"], user_text, parse_mode="Markdown", reply_markup=get_webapp_keyboard())
    
    try:
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n💸 **Возврат средств оформлен**",
            parse_mode="Markdown"
        )
    except:
        pass
    
    await callback.answer("💸 Возврат средств оформлен, пользователь уведомлён.")

# ============ КОМАНДЫ АДМИНИСТРАТОРА ============

@router.message(Command("stats"))
async def show_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    async with aiosqlite.connect('shop_bot.db') as db:
        async with db.execute('SELECT COUNT(*) FROM users') as cursor:
            total_users = (await cursor.fetchone())[0]
        
        async with db.execute('SELECT COUNT(*) FROM orders') as cursor:
            total_orders = (await cursor.fetchone())[0]
        
        async with db.execute('SELECT COUNT(*) FROM orders WHERE status = "completed"') as cursor:
            completed = (await cursor.fetchone())[0]
        
        async with db.execute('SELECT COUNT(*) FROM orders WHERE status = "pending"') as cursor:
            pending = (await cursor.fetchone())[0]
        
        async with db.execute('SELECT SUM(product_price) FROM orders WHERE status = "completed"') as cursor:
            revenue = (await cursor.fetchone())[0] or 0
    
    text = (
        f"{EMOJI['diamond']} **СТАТИСТИКА БОТА**\n\n"
        f"👥 Пользователей: **{total_users}**\n"
        f"📦 Всего заказов: **{total_orders}**\n"
        f"✅ Завершено: **{completed}**\n"
        f"⏳ Ожидают: **{pending}**\n"
        f"💰 Выручка: **{revenue}₽**"
    )
    
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("broadcast"))
async def start_broadcast(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await state.set_state(BroadcastStates.waiting_for_message)
    await message.answer(
        f"{EMOJI['fire']} **РЕЖИМ РАССЫЛКИ**\n\n"
        "Отправьте сообщение для рассылки.\n"
        "Можно отправить текст, фото или видео.\n\n"
        "/cancel для отмены",
        parse_mode="Markdown"
    )

@router.message(Command("cancel"))
async def cancel_action(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await state.clear()
    await message.answer(f"{EMOJI['cross']} Действие отменено")

@router.message(BroadcastStates.waiting_for_message)
async def receive_broadcast(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    broadcast_data = {
        'text': message.text or message.caption,
        'photo': message.photo[-1].file_id if message.photo else None,
        'video': message.video.file_id if message.video else None,
    }
    
    await state.update_data(broadcast_data=broadcast_data)
    await state.set_state(BroadcastStates.waiting_for_confirmation)
    
    async with aiosqlite.connect('shop_bot.db') as db:
        async with db.execute('SELECT COUNT(*) FROM users') as cursor:
            user_count = (await cursor.fetchone())[0]
    
    text = (
        f"{EMOJI['alert']} **ПОДТВЕРЖДЕНИЕ**\n\n"
        f"Получателей: **{user_count}**\n\n"
        "Отправить?\n"
        "**ДА** - отправить\n"
        "**НЕТ** - отменить"
    )
    
    await message.answer(text, parse_mode="Markdown")

@router.message(BroadcastStates.waiting_for_confirmation)
async def confirm_broadcast(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    
    if message.text and message.text.upper() == "ДА":
        data = await state.get_data()
        broadcast_data = data.get('broadcast_data')
        
        async with aiosqlite.connect('shop_bot.db') as db:
            async with db.execute('SELECT user_id FROM users') as cursor:
                users = await cursor.fetchall()
        
        success = 0
        failed = 0
        status_msg = await message.answer(f"{EMOJI['lightning']} Рассылка началась...")
        
        for user_id, in users:
            try:
                if broadcast_data['photo']:
                    await bot.send_photo(
                        user_id,
                        photo=broadcast_data['photo'],
                        caption=broadcast_data['text'],
                        parse_mode="Markdown"
                    )
                elif broadcast_data['video']:
                    await bot.send_video(
                        user_id,
                        video=broadcast_data['video'],
                        caption=broadcast_data['text'],
                        parse_mode="Markdown"
                    )
                else:
                    await bot.send_message(
                        user_id,
                        text=broadcast_data['text'],
                        parse_mode="Markdown"
                    )
                success += 1
            except:
                failed += 1
        
        await status_msg.edit_text(
            f"{EMOJI['check']} **Рассылка завершена!**\n\n"
            f"✅ Успешно: **{success}**\n"
            f"❌ Ошибок: **{failed}**",
            parse_mode="Markdown"
        )
        await state.clear()
    
    elif message.text and message.text.upper() == "НЕТ":
        await message.answer(f"{EMOJI['cross']} Рассылка отменена")
        await state.clear()
    
    else:
        await message.answer("Ответьте **ДА** или **НЕТ**", parse_mode="Markdown")

@router.message(Command("refund"))
async def manual_refund(message: Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        # Извлекаем все ID после команды
        ids_text = message.text.replace("/refund", "").strip()
        
        if not ids_text:
            await message.answer(
                f"{EMOJI['alert']} **Использование:**\n"
                "`/refund ID1, ID2, ID3...`\n\n"
                "Примеры:\n"
                "• `/refund 5` — один заказ\n"
                "• `/refund 5, 7, 12` — несколько заказов",
                parse_mode="Markdown"
            )
            return
        
        # Разделяем по запятой и убираем пробелы
        order_ids = [int(id.strip()) for id in ids_text.split(",")]
        
        success_count = 0
        failed_count = 0
        results = []
        
        status_msg = await message.answer(
            f"{EMOJI['lightning']} Обработка возвратов...\n"
            f"Всего заказов: {len(order_ids)}",
            parse_mode="Markdown"
        )
        
        for order_id in order_ids:
            try:
                order = await get_order(order_id)
                
                if not order:
                    results.append(f"❌ #{order_id} — не найден")
                    failed_count += 1
                    continue
                
                await update_order_status(order_id, "refunded")
                
                user_text = (
                    f"❗ **Искренне приносим извинения за доставленные неудобства**\n\n"
                    f"{EMOJI['alert']} По заказу **#{order_id}** ({order['product_name']}) обнаружена ошибка в платёжных реквизитах.\n\n"
                    f"{EMOJI['money']} **Возврат средств инициирован**\n"
                    f"{EMOJI['clock']} Срок возврата: до 3-х рабочих дней\n"
                    f"{EMOJI['alert']} Точное время зачисления зависит от вашего банка\n\n"
                    f"━━━━━━━━━━━━━━━━━━━\n\n"
                    f"{EMOJI['berry']} **В качестве компенсации** мы дарим вам промокод:\n"
                    f"**`REF20`** — скидка **20%** на следующий заказ!\n\n"
                    f"━━━━━━━━━━━━━━━━━━━\n\n"
                    f"{EMOJI['fire']} Чтобы получить товар по **обновлённым реквизитам** и с промокодом, оформите заказ повторно через наш магазин.\n\n"
                    f"{EMOJI['heart']} Благодарим за понимание!"
                )
                
                await bot.send_message(
                    order["user_id"], 
                    user_text, 
                    parse_mode="Markdown", 
                    reply_markup=get_webapp_keyboard()
                )
                
                results.append(f"✅ #{order_id} — возврат оформлен")
                success_count += 1
                
            except Exception as e:
                results.append(f"❌ #{order_id} — ошибка: {str(e)}")
                failed_count += 1
        
        # Формируем итоговый отчёт
        report = (
            f"{EMOJI['check']} **ОТЧЁТ О ВОЗВРАТАХ**\n\n"
            f"✅ Успешно: **{success_count}**\n"
            f"❌ Ошибок: **{failed_count}**\n\n"
            f"**Детали:**\n"
        )
        
        for result in results:
            report += f"{result}\n"
        
        await status_msg.edit_text(report, parse_mode="Markdown")
    
    except ValueError:
        await message.answer(
            f"{EMOJI['cross']} **Ошибка формата!**\n\n"
            "ID заказов должны быть числами.\n"
            "Используйте: `/refund 5, 7, 12`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"{EMOJI['cross']} Ошибка: {str(e)}")

# ============ ПРОМОКОДЫ ============

@router.message(Command("addpromo"))
async def start_add_promo(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await state.set_state(PromoAdminStates.waiting_for_code)
    await message.answer(
        f"{EMOJI['berry']} **СОЗДАНИЕ ПРОМОКОДА**\n\n"
        "Шаг 1/4: Введите код промокода\n"
        "_(Например: FREE10)_",
        parse_mode="Markdown"
    )

@router.message(PromoAdminStates.waiting_for_code)
async def get_promo_code(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    code = message.text.strip().upper()
    await state.update_data(promo_code=code)
    await state.set_state(PromoAdminStates.waiting_for_discount)
    await message.answer(
        "Шаг 2/4: Введите размер скидки в %\n"
        "_(Например: 10)_",
        parse_mode="Markdown"
    )

@router.message(PromoAdminStates.waiting_for_discount)
async def get_promo_discount(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        discount = int(message.text.strip())
        await state.update_data(discount=discount)
        await state.set_state(PromoAdminStates.waiting_for_description)
        await message.answer("Шаг 3/4: Введите описание", parse_mode="Markdown")
    except:
        await message.answer(f"{EMOJI['cross']} Введите число!")

@router.message(PromoAdminStates.waiting_for_description)
async def get_promo_desc(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await state.update_data(description=message.text.strip())
    await state.set_state(PromoAdminStates.waiting_for_max_uses)
    await message.answer("Шаг 4/4: Макс. использований (0 = безлимит)", parse_mode="Markdown")

@router.message(PromoAdminStates.waiting_for_max_uses)
async def create_promo(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        max_uses = int(message.text.strip())
        data = await state.get_data()
        
        success = await add_promocode(
            data['promo_code'],
            data['discount'],
            data['description'],
            max_uses
        )
        
        if success:
            await message.answer(
                f"{EMOJI['check']} **Промокод создан!**\n\n"
                f"Код: `{data['promo_code']}`\n"
                f"Скидка: {data['discount']}%",
                parse_mode="Markdown"
            )
        else:
            await message.answer(f"{EMOJI['cross']} Такой промокод уже существует!")
        
        await state.clear()
    except:
        await message.answer(f"{EMOJI['cross']} Введите число!")

@router.message(Command("promos"))
async def list_promos(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    promos = await get_all_promocodes()
    
    if not promos:
        await message.answer("Промокодов пока нет.\n\n/addpromo для создания")
        return
    
    text = f"{EMOJI['berry']} **ПРОМОКОДЫ**\n\n"
    for p in promos:
        text += f"`{p['code']}` - {p['discount']}% ({'🟢' if p['is_active'] else '🔴'})\n"
    
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("delpromo"))
async def delete_promo(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        code = message.text.split()[1].upper()
        await delete_promocode(code)
        await message.answer(f"{EMOJI['check']} Промокод удалён!")
    except:
        await message.answer("Использование: /delpromo КОД")

@router.message(Command("togglepromo"))
async def toggle_promo(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        code = message.text.split()[1].upper()
        await toggle_promocode(code)
        await message.answer(f"{EMOJI['check']} Статус изменён!")
    except:
        await message.answer("Использование: /togglepromo КОД")


# =========================
# РАССЫЛКИ / ЛИЧНЫЕ СООБЩЕНИЯ
# =========================


async def dm_single_user(message: Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Использование: /dm <user_id> <сообщение>")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("user_id должен быть числом.")
        return
    text = parts[2].strip()
    if not text:
        await message.answer("Сообщение пустое.")
        return
    try:
        await bot.send_message(uid, text)
        await message.answer(f"{EMOJI['check']} Отправлено пользователю {uid}.")
    except Exception as e:
        await message.answer(f"{EMOJI['cross']} Не удалось отправить пользователю {uid}.\n{e}")

@router.message(Command("dm_multi"))
async def dm_multi_users(message: Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Использование: /dm_multi <id1,id2,...> <сообщение>")
        return
    raw_ids = [p.strip() for p in parts[1].split(",") if p.strip()]
    try:
        user_ids = [int(x) for x in raw_ids]
    except ValueError:
        await message.answer("ID должны быть числами, через запятую.")
        return
    text = (parts[2] or "").strip()
    if not text:
        await message.answer("Сообщение пустое.")
        return
    existing = await get_existing_user_ids(user_ids)
    if not existing:
        await message.answer("Ни один ID не найден в базе пользователей.")
        return
    sent = 0
    failed = 0
    for uid in existing:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1
    await message.answer(f"{EMOJI['check']} Готово. Отправлено: {sent}/{len(existing)}. Ошибок: {failed}.")

# =========================
# РАССЫЛКИ / ЛИЧНЫЕ СООБЩЕНИЯ — С ПОДТВЕРЖДЕНИЕМ
# =========================

class BuyersBroadcastStates(StatesGroup):
    waiting_for_message = State()
    confirm = State()

@router.message(Command("buyers_broadcast"))
async def buyers_broadcast_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.set_state(BuyersBroadcastStates.waiting_for_message)
    await message.answer(
        f"{EMOJI.get('megaphone','📣')} Отправь текст рассылки для покупателей.\n"
        f"Поддерживается только текст без форматирования."
    )

@router.message(BuyersBroadcastStates.waiting_for_message)
async def buyers_broadcast_preview(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer("Пустое сообщение. Пришли текст ещё раз.")
        return
    await state.update_data(broadcast_text=text)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_broadcast"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast"),
    ]])
    await state.set_state(BuyersBroadcastStates.confirm)
    await message.answer(f"**Предпросмотр рассылки:**\n\n{text}", reply_markup=kb, parse_mode=None)

@router.callback_query(F.data == "confirm_broadcast")
async def buyers_broadcast_send(callback: CallbackQuery, bot: Bot, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    user_ids = await get_buyer_user_ids(statuses=("completed",))
    total = len(user_ids)
    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except (TelegramForbiddenError, TelegramNotFound, TelegramBadRequest):
            failed += 1
        except TelegramRetryAfter as e:
            import asyncio
            await asyncio.sleep(getattr(e, "retry_after", 1))
            try:
                await bot.send_message(uid, text)
                sent += 1
            except Exception:
                failed += 1
        except Exception:
            failed += 1
    await state.clear()
    try:
        await callback.message.edit_text(f"Готово: отправлено {sent}/{total}. Ошибок: {failed}.")
    except:
        await callback.message.answer(f"Готово: отправлено {sent}/{total}. Ошибок: {failed}.")
    await callback.answer("Рассылка завершена")

@router.callback_query(F.data == "cancel_broadcast")
async def buyers_broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    await state.clear()
    try:
        await callback.message.edit_text("❌ Рассылка отменена.")
    except:
        await callback.message.answer("❌ Рассылка отменена.")
    await callback.answer()

# ---- DM одному пользователю ----

class AdminDMState(StatesGroup):
    confirm = State()

@router.message(Command("dm"))
async def dm_single_user(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Использование: /dm <user_id> <сообщение>")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("user_id должен быть числом.")
        return
    text = parts[2].strip()
    if not text:
        await message.answer("Сообщение пустое.")
        return
    await state.set_state(AdminDMState.confirm)
    await state.update_data(dm_uid=uid, dm_text=text)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_dm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_dm"),
    ]])
    await message.answer(f"**Предпросмотр сообщения для {uid}:**\n\n{text}", reply_markup=kb, parse_mode=None)

@router.callback_query(F.data == "confirm_dm")
async def dm_confirm(callback: CallbackQuery, bot: Bot, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    data = await state.get_data()
    uid = data.get("dm_uid")
    text = data.get("dm_text", "")
    ok = True
    try:
        await bot.send_message(uid, text)
    except Exception:
        ok = False
    await state.clear()
    try:
        await callback.message.edit_text("✅ Отправлено." if ok else "❌ Не удалось отправить.")
    except:
        pass
    await callback.answer()

@router.callback_query(F.data == "cancel_dm")
async def dm_cancel(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    await state.clear()
    try:
        await callback.message.edit_text("❌ Отправка отменена.")
    except:
        pass
    await callback.answer()

# ---- DM нескольким пользователям ----

class AdminDMMultiState(StatesGroup):
    confirm = State()

@router.message(Command("dm_multi"))
async def dm_multi_users(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Использование: /dm_multi <id1,id2,...> <сообщение>")
        return
    raw_ids = [p.strip() for p in parts[1].split(",") if p.strip()]
    try:
        user_ids = [int(x) for x in raw_ids]
    except ValueError:
        await message.answer("ID должны быть числами, через запятую.")
        return
    text = (parts[2] or "").strip()
    if not text:
        await message.answer("Сообщение пустое.")
        return
    existing = await get_existing_user_ids(user_ids)
    if not existing:
        await message.answer("Ни один ID не найден в базе пользователей.")
        return
    await state.set_state(AdminDMMultiState.confirm)
    await state.update_data(dm_multi_ids=existing, dm_multi_text=text)
    ids_preview = ", ".join(map(str, existing[:10])) + ("..." if len(existing) > 10 else "")
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_dm_multi"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_dm_multi"),
    ]])
    await message.answer(
        f"**Предпросмотр сообщения ({len(existing)} получателей):**\nID: {ids_preview}\n\n{text}",
        reply_markup=kb,
        parse_mode=None
    )

@router.callback_query(F.data == "confirm_dm_multi")
async def dm_multi_confirm(callback: CallbackQuery, bot: Bot, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    data = await state.get_data()
    ids = data.get("dm_multi_ids", [])
    text = data.get("dm_multi_text", "")
    sent = 0
    failed = 0
    for uid in ids:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1
    await state.clear()
    try:
        await callback.message.edit_text(f"Готово. Отправлено: {sent}/{len(ids)}. Ошибок: {failed}.")
    except:
        pass
    await callback.answer()

@router.callback_query(F.data == "cancel_dm_multi")
async def dm_multi_cancel(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    await state.clear()
    try:
        await callback.message.edit_text("❌ Отправка отменена.")
    except:
        pass
    await callback.answer()
