# Примеры кода для реализации

## 📝 Содержание

1. [База данных](#база-данных)
2. [Сервисный слой](#сервисный-слой)
3. [Обработчики](#обработчики)
4. [Планировщик](#планировщик)

---

## База данных

### database.py - Добавление таблиц

```python
async def init_recurring_tables():
    """Инициализация таблиц для повторяющихся рассылок"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица шаблонов рассылок
        await db.execute('''
            CREATE TABLE IF NOT EXISTS recurring_broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                audience TEXT NOT NULL,
                text TEXT NOT NULL,
                parse_mode TEXT DEFAULT 'HTML',
                keyboard_json TEXT,
                schedule_pattern TEXT NOT NULL,
                schedule_time TEXT NOT NULL,
                schedule_days TEXT,
                schedule_day_of_month INTEGER,
                timezone TEXT DEFAULT 'Europe/Moscow',
                is_active INTEGER DEFAULT 1,
                last_sent_at TIMESTAMP,
                next_send_at TIMESTAMP,
                total_sends INTEGER DEFAULT 0,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица логов отправок
        await db.execute('''
            CREATE TABLE IF NOT EXISTS recurring_send_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recurring_id INTEGER NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL,
                error_message TEXT,
                recipients_count INTEGER,
                FOREIGN KEY (recurring_id) REFERENCES recurring_broadcasts(id)
            )
        ''')
        
        await db.commit()


async def create_recurring_broadcast(
    name: str,
    audience: str,
    text: str,
    keyboard_json: str,
    schedule_pattern: str,
    schedule_time: str,
    schedule_days: str = None,
    schedule_day_of_month: int = None,
    timezone: str = "Europe/Moscow",
    created_by: int = None
) -> int:
    """Создание повторяющейся рассылки"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('''
            INSERT INTO recurring_broadcasts (
                name, audience, text, keyboard_json,
                schedule_pattern, schedule_time, schedule_days,
                schedule_day_of_month, timezone, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            name, audience, text, keyboard_json,
            schedule_pattern, schedule_time, schedule_days,
            schedule_day_of_month, timezone, created_by
        ))
        await db.commit()
        return cursor.lastrowid


async def get_recurring_broadcast(recurring_id: int):
    """Получение рассылки по ID"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            'SELECT * FROM recurring_broadcasts WHERE id = ?',
            (recurring_id,)
        ) as cursor:
            return await cursor.fetchone()


async def list_recurring_broadcasts(active_only: bool = False):
    """Список всех рассылок"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        query = 'SELECT * FROM recurring_broadcasts'
        if active_only:
            query += ' WHERE is_active = 1'
        query += ' ORDER BY created_at DESC'
        
        async with db.execute(query) as cursor:
            return await cursor.fetchall()


async def update_recurring_broadcast_status(recurring_id: int, is_active: bool):
    """Включение/выключение рассылки"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'UPDATE recurring_broadcasts SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (1 if is_active else 0, recurring_id)
        )
        await db.commit()


async def update_recurring_broadcast_stats(
    recurring_id: int,
    last_sent_at: str,
    next_send_at: str,
    increment_sends: bool = True
):
    """Обновление статистики после отправки"""
    async with aiosqlite.connect(DB_NAME) as db:
        if increment_sends:
            await db.execute('''
                UPDATE recurring_broadcasts 
                SET last_sent_at = ?, 
                    next_send_at = ?, 
                    total_sends = total_sends + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (last_sent_at, next_send_at, recurring_id))
        else:
            await db.execute('''
                UPDATE recurring_broadcasts 
                SET last_sent_at = ?, 
                    next_send_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (last_sent_at, next_send_at, recurring_id))
        await db.commit()


async def log_recurring_send(
    recurring_id: int,
    status: str,
    error_message: str = None,
    recipients_count: int = 0
):
    """Логирование отправки"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO recurring_send_log (
                recurring_id, status, error_message, recipients_count
            ) VALUES (?, ?, ?, ?)
        ''', (recurring_id, status, error_message, recipients_count))
        await db.commit()


async def get_recurring_send_history(recurring_id: int, limit: int = 10):
    """История отправок"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT * FROM recurring_send_log 
            WHERE recurring_id = ? 
            ORDER BY sent_at DESC 
            LIMIT ?
        ''', (recurring_id, limit)) as cursor:
            return await cursor.fetchall()


async def delete_recurring_broadcast(recurring_id: int):
    """Удаление рассылки"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Удаляем логи
        await db.execute(
            'DELETE FROM recurring_send_log WHERE recurring_id = ?',
            (recurring_id,)
        )
        # Удаляем рассылку
        await db.execute(
            'DELETE FROM recurring_broadcasts WHERE id = ?',
            (recurring_id,)
        )
        await db.commit()
```

---

## Сервисный слой

### services/recurring_service.py

```python
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
from typing import Optional

from database import (
    get_recurring_broadcast,
    update_recurring_broadcast_stats,
    log_recurring_send,
    list_recurring_broadcasts,
    create_order  # Используем существующую функцию для создания задач
)


class RecurringBroadcastService:
    """Сервис для работы с повторяющимися рассылками"""
    
    @staticmethod
    def calculate_next_send_time(
        pattern: str,
        schedule_time: str,
        schedule_days: Optional[str] = None,
        day_of_month: Optional[int] = None,
        timezone: str = "Europe/Moscow",
        from_time: Optional[datetime] = None
    ) -> datetime:
        """
        Расчет следующего времени отправки
        
        Args:
            pattern: 'daily', 'weekly', 'monthly'
            schedule_time: 'HH:MM'
            schedule_days: JSON массив дней недели для weekly [1,2,3]
            day_of_month: День месяца для monthly
            timezone: Часовой пояс
            from_time: От какого времени считать (по умолчанию - сейчас)
        
        Returns:
            datetime: Следующее время отправки в UTC
        """
        tz = ZoneInfo(timezone)
        current = from_time or datetime.now(tz)
        
        # Парсим время
        hour, minute = map(int, schedule_time.split(':'))
        
        if pattern == 'daily':
            # Ежедневно
            next_time = current.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0
            )
            
            # Если время уже прошло сегодня, берем завтра
            if next_time <= current:
                next_time += timedelta(days=1)
        
        elif pattern == 'weekly':
            # Еженедельно
            if not schedule_days:
                raise ValueError("schedule_days required for weekly pattern")
            
            days = json.loads(schedule_days)  # [1, 3, 5] - пн, ср, пт
            current_weekday = current.isoweekday()  # 1-7
            
            # Ищем ближайший день
            next_time = None
            for day in sorted(days):
                days_ahead = day - current_weekday
                if days_ahead < 0:
                    days_ahead += 7
                
                candidate = current + timedelta(days=days_ahead)
                candidate = candidate.replace(
                    hour=hour,
                    minute=minute,
                    second=0,
                    microsecond=0
                )
                
                if candidate > current:
                    next_time = candidate
                    break
            
            # Если не нашли на этой неделе, берем первый день следующей
            if not next_time:
                days_ahead = (days[0] - current_weekday) % 7 + 7
                next_time = current + timedelta(days=days_ahead)
                next_time = next_time.replace(
                    hour=hour,
                    minute=minute,
                    second=0,
                    microsecond=0
                )
        
        elif pattern == 'monthly':
            # Ежемесячно
            if not day_of_month:
                raise ValueError("day_of_month required for monthly pattern")
            
            # Пробуем текущий месяц
            try:
                next_time = current.replace(
                    day=day_of_month,
                    hour=hour,
                    minute=minute,
                    second=0,
                    microsecond=0
                )
            except ValueError:
                # День не существует в этом месяце (например, 31 февраля)
                # Берем последний день месяца
                next_month = current.replace(day=1) + timedelta(days=32)
                next_time = next_month.replace(day=1) - timedelta(days=1)
                next_time = next_time.replace(
                    hour=hour,
                    minute=minute,
                    second=0,
                    microsecond=0
                )
            
            # Если время уже прошло, берем следующий месяц
            if next_time <= current:
                if current.month == 12:
                    next_time = next_time.replace(year=current.year + 1, month=1)
                else:
                    next_time = next_time.replace(month=current.month + 1)
                
                # Снова проверяем существование дня
                try:
                    next_time = next_time.replace(day=day_of_month)
                except ValueError:
                    # Берем последний день месяца
                    next_month = next_time.replace(day=1) + timedelta(days=32)
                    next_time = next_month.replace(day=1) - timedelta(days=1)
        
        else:
            raise ValueError(f"Unknown pattern: {pattern}")
        
        # Конвертируем в UTC
        return next_time.astimezone(ZoneInfo("UTC"))
    
    
    @staticmethod
    async def create_scheduled_task_from_recurring(recurring_id: int) -> Optional[int]:
        """
        Создание задачи в scheduled_broadcasts из recurring broadcast
        
        Returns:
            int: ID созданной задачи или None при ошибке
        """
        from services import scheduled_repo
        
        recurring = await get_recurring_broadcast(recurring_id)
        if not recurring or not recurring['is_active']:
            return None
        
        # Рассчитываем следующее время
        next_time = RecurringBroadcastService.calculate_next_send_time(
            pattern=recurring['schedule_pattern'],
            schedule_time=recurring['schedule_time'],
            schedule_days=recurring.get('schedule_days'),
            day_of_month=recurring.get('schedule_day_of_month'),
            timezone=recurring['timezone']
        )
        
        # Создаем задачу
        await scheduled_repo.ensure_schema()
        task_id = await scheduled_repo.create(
            audience=recurring['audience'],
            text=recurring['text'],
            parse_mode=recurring['parse_mode'],
            keyboard_json=recurring['keyboard_json'],
            scheduled_at_utc=next_time.isoformat(),
            tz=recurring['timezone'],
            created_by=recurring['created_by'],
            recurring_id=recurring_id  # Связываем с recurring
        )
        
        # Обновляем next_send_at
        await update_recurring_broadcast_stats(
            recurring_id=recurring_id,
            last_sent_at=recurring.get('last_sent_at'),
            next_send_at=next_time.isoformat(),
            increment_sends=False
        )
        
        return task_id
    
    
    @staticmethod
    async def process_completed_broadcast(scheduled_task_id: int, success: bool, error: str = None):
        """
        Обработка завершенной рассылки
        
        Args:
            scheduled_task_id: ID задачи из scheduled_broadcasts
            success: Успешно ли выполнена
            error: Сообщение об ошибке (если есть)
        """
        from services import scheduled_repo
        
        # Получаем задачу
        task = await scheduled_repo.get_by_id(scheduled_task_id)
        if not task:
            return
        
        # Проверяем, связана ли с recurring
        recurring_id = task.get('recurring_id')
        if not recurring_id:
            return  # Это обычная одноразовая рассылка
        
        # Логируем отправку
        await log_recurring_send(
            recurring_id=recurring_id,
            status='success' if success else 'failed',
            error_message=error,
            recipients_count=task.get('recipients_count', 0)
        )
        
        # Обновляем статистику
        now = datetime.now(ZoneInfo("UTC"))
        await update_recurring_broadcast_stats(
            recurring_id=recurring_id,
            last_sent_at=now.isoformat(),
            next_send_at=None,  # Будет установлено при создании следующей задачи
            increment_sends=success  # Увеличиваем счетчик только при успехе
        )
        
        # Создаем следующую задачу (даже если была ошибка)
        await RecurringBroadcastService.create_scheduled_task_from_recurring(recurring_id)
    
    
    @staticmethod
    async def sync_recurring_schedules(bot):
        """
        Синхронизация расписаний при старте бота
        Проверяет все активные recurring broadcasts и создает задачи если нужно
        """
        from services import scheduled_repo
        
        active_broadcasts = await list_recurring_broadcasts(active_only=True)
        
        for broadcast in active_broadcasts:
            recurring_id = broadcast['id']
            
            # Проверяем, есть ли уже запланированная задача
            pending_tasks = await scheduled_repo.list_by_recurring_id(recurring_id)
            
            if not pending_tasks:
                # Нет задачи - создаем
                await RecurringBroadcastService.create_scheduled_task_from_recurring(recurring_id)
```

---

## Обработчики

### handlers/recurring_broadcast.py (создание)

```python
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_ID
from database import create_recurring_broadcast
from services.recurring_service import RecurringBroadcastService

router = Router(name="recurring_broadcast")


class RecurringStates(StatesGroup):
    waiting_name = State()
    waiting_text = State()
    adding_buttons = State()
    waiting_photo = State()
    waiting_pattern = State()
    waiting_days = State()
    waiting_day_of_month = State()
    waiting_time = State()
    confirm = State()


def _admin_only(message: Message) -> bool:
    return message.from_user and message.from_user.id == ADMIN_ID


@router.message(Command("recurring_broadcast"))
async def cmd_recurring_broadcast(message: Message, state: FSMContext):
    """Создание повторяющейся рассылки для всех"""
    if not _admin_only(message):
        return
    
    await state.clear()
    await state.update_data(audience="all")
    await message.answer(
        "📣 <b>Создание повторяющейся рассылки</b>\n\n"
        "Введите название рассылки (для удобства управления):",
        parse_mode="HTML"
    )
    await state.set_state(RecurringStates.waiting_name)


@router.message(RecurringStates.waiting_name)
async def got_name(message: Message, state: FSMContext):
    """Получение названия"""
    if not _admin_only(message):
        return
    
    name = message.text.strip()
    if not name or len(name) > 100:
        await message.answer("❌ Название должно быть от 1 до 100 символов")
        return
    
    await state.update_data(name=name)
    await message.answer(
        f"✅ Название: <b>{name}</b>\n\n"
        "Теперь введите текст рассылки (HTML разрешён):",
        parse_mode="HTML"
    )
    await state.set_state(RecurringStates.waiting_text)


# ... (аналогично broadcast_scheduler.py для текста, кнопок, фото)


@router.callback_query(RecurringStates.adding_buttons, F.data == "btn_done")
async def btn_done(callback: CallbackQuery, state: FSMContext):
    """Переход к выбору расписания"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Ежедневно", callback_data="pattern_daily")
    kb.button(text="📆 Еженедельно", callback_data="pattern_weekly")
    kb.button(text="📊 Ежемесячно", callback_data="pattern_monthly")
    kb.adjust(1)
    
    await callback.message.edit_text(
        "⏰ Выберите частоту рассылки:",
        reply_markup=kb.as_markup()
    )
    await state.set_state(RecurringStates.waiting_pattern)
    await callback.answer()


@router.callback_query(RecurringStates.waiting_pattern, F.data.startswith("pattern_"))
async def got_pattern(callback: CallbackQuery, state: FSMContext):
    """Получение паттерна"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    pattern = callback.data.split("_")[1]  # daily, weekly, monthly
    await state.update_data(schedule_pattern=pattern)
    
    if pattern == "daily":
        # Для ежедневной сразу спрашиваем время
        await callback.message.edit_text(
            "🕐 Введите время отправки в формате <code>HH:MM</code> (по МСК):\n\n"
            "Например: <code>09:00</code>",
            parse_mode="HTML"
        )
        await state.set_state(RecurringStates.waiting_time)
    
    elif pattern == "weekly":
        # Для еженедельной спрашиваем дни
        kb = InlineKeyboardBuilder()
        days = [
            ("Пн", 1), ("Вт", 2), ("Ср", 3), ("Чт", 4),
            ("Пт", 5), ("Сб", 6), ("Вс", 7)
        ]
        for day_name, day_num in days:
            kb.button(text=day_name, callback_data=f"day_{day_num}")
        kb.button(text="✅ Готово", callback_data="days_done")
        kb.adjust(4, 3, 1)
        
        await state.update_data(selected_days=[])
        await callback.message.edit_text(
            "📆 Выберите дни недели для рассылки:",
            reply_markup=kb.as_markup()
        )
        await state.set_state(RecurringStates.waiting_days)
    
    elif pattern == "monthly":
        # Для ежемесячной спрашиваем день месяца
        await callback.message.edit_text(
            "📊 Введите день месяца (1-31):\n\n"
            "Например: <code>15</code> (15 число каждого месяца)",
            parse_mode="HTML"
        )
        await state.set_state(RecurringStates.waiting_day_of_month)
    
    await callback.answer()


# ... (обработчики для weekly и monthly)


@router.message(RecurringStates.waiting_time)
async def got_time(message: Message, state: FSMContext):
    """Получение времени"""
    if not _admin_only(message):
        return
    
    time_str = message.text.strip()
    
    # Валидация формата HH:MM
    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except:
        await message.answer(
            "❌ Неверный формат времени. Используйте <code>HH:MM</code>\n"
            "Например: <code>09:00</code>",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(schedule_time=time_str)
    
    # Показываем финальное подтверждение
    await show_confirmation(message, state)


async def show_confirmation(message: Message, state: FSMContext):
    """Показ финального подтверждения"""
    data = await state.get_data()
    
    # Формируем описание расписания
    pattern = data['schedule_pattern']
    time = data['schedule_time']
    
    if pattern == 'daily':
        schedule_desc = f"📅 Каждый день в {time} МСК"
    elif pattern == 'weekly':
        days = data.get('selected_days', [])
        day_names = {1: 'Пн', 2: 'Вт', 3: 'Ср', 4: 'Чт', 5: 'Пт', 6: 'Сб', 7: 'Вс'}
        days_str = ', '.join(day_names[d] for d in sorted(days))
        schedule_desc = f"📆 Каждую неделю: {days_str} в {time} МСК"
    else:  # monthly
        day = data.get('schedule_day_of_month')
        schedule_desc = f"📊 Каждый месяц {day} числа в {time} МСК"
    
    # Рассчитываем первую отправку
    next_send = RecurringBroadcastService.calculate_next_send_time(
        pattern=pattern,
        schedule_time=time,
        schedule_days=data.get('schedule_days'),
        day_of_month=data.get('schedule_day_of_month')
    )
    
    # Показываем предпросмотр сообщения
    # ... (аналогично broadcast_scheduler.py)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Создать", callback_data="recurring_confirm")
    kb.button(text="📤 Тест", callback_data="recurring_test")
    kb.button(text="✏️ Изменить", callback_data="recurring_edit")
    kb.button(text="❌ Отмена", callback_data="recurring_cancel")
    kb.adjust(2, 2)
    
    await message.answer(
        f"⏱ <b>Подтверждение рассылки</b>\n\n"
        f"📝 Название: {data['name']}\n"
        f"{schedule_desc}\n"
        f"⏰ Первая отправка: {next_send.strftime('%Y-%m-%d %H:%M')} МСК",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await state.set_state(RecurringStates.confirm)


@router.callback_query(RecurringStates.confirm, F.data == "recurring_confirm")
async def recurring_confirm(callback: CallbackQuery, state: FSMContext):
    """Подтверждение создания"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer()
        return
    
    data = await state.get_data()
    
    # Создаем recurring broadcast
    recurring_id = await create_recurring_broadcast(
        name=data['name'],
        audience=data['audience'],
        text=data['text'],
        keyboard_json=data.get('keyboard_json', '[]'),
        schedule_pattern=data['schedule_pattern'],
        schedule_time=data['schedule_time'],
        schedule_days=data.get('schedule_days'),
        schedule_day_of_month=data.get('schedule_day_of_month'),
        created_by=callback.from_user.id
    )
    
    # Создаем первую задачу
    task_id = await RecurringBroadcastService.create_scheduled_task_from_recurring(recurring_id)
    
    await state.clear()
    await callback.message.edit_text(
        f"✅ <b>Повторяющаяся рассылка создана!</b>\n\n"
        f"ID: #{recurring_id}\n"
        f"Первая задача: #{task_id}\n\n"
        f"Используйте /recurring_list для управления",
        parse_mode="HTML"
    )
    await callback.answer("Создано!")
```

Это основные примеры кода. Полная реализация будет включать больше деталей, но структура будет такой.
