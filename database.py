import aiosqlite

DB_NAME = 'shop_bot.db'

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_name TEXT,
                product_price INTEGER,
                original_price INTEGER,
                promo_code TEXT,
                payment_method TEXT,
                status TEXT DEFAULT 'pending',
                photo_file_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS promocodes (
                code TEXT PRIMARY KEY,
                discount INTEGER,
                description TEXT,
                max_uses INTEGER DEFAULT 0,
                current_uses INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для повторяющихся рассылок
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
        
        # Таблица логов отправок повторяющихся рассылок
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

async def add_user(user_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)',
            (user_id, username, first_name)
        )
        await db.commit()

async def create_order(user_id: int, product_name: str, product_price: int, payment_method: str, original_price: int = None, promo_code: str = None):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            'INSERT INTO orders (user_id, product_name, product_price, original_price, promo_code, payment_method) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, product_name, product_price, original_price or product_price, promo_code, payment_method)
        )
        await db.commit()
        return cursor.lastrowid

async def update_order_photo(order_id: int, photo_file_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE orders SET photo_file_id = ? WHERE order_id = ?', (photo_file_id, order_id))
        await db.commit()

async def update_order_status(order_id: int, status: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE orders SET status = ? WHERE order_id = ?', (status, order_id))
        await db.commit()

async def get_order(order_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM orders WHERE order_id = ?', (order_id,)) as cursor:
            return await cursor.fetchone()

async def add_promocode(code: str, discount: int, description: str, max_uses: int = 0):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute('INSERT INTO promocodes (code, discount, description, max_uses) VALUES (?, ?, ?, ?)',
                           (code.upper(), discount, description, max_uses))
            await db.commit()
            return True
        except:
            return False

async def get_promocode(code: str):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM promocodes WHERE code = ? AND is_active = 1', (code.upper(),)) as cursor:
            return await cursor.fetchone()

async def use_promocode(code: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE promocodes SET current_uses = current_uses + 1 WHERE code = ?', (code.upper(),))
        await db.commit()

async def delete_promocode(code: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM promocodes WHERE code = ?', (code.upper(),))
        await db.commit()

async def get_all_promocodes():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM promocodes ORDER BY created_at DESC') as cursor:
            return await cursor.fetchall()

async def toggle_promocode(code: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE promocodes SET is_active = NOT is_active WHERE code = ?', (code.upper(),))
        await db.commit()



async def get_buyer_user_ids(statuses: tuple = ("completed",)):
    """Возвращает user_id с заказами в указанных статусах (по умолчанию 'completed')."""
    placeholders = ",".join(["?"] * len(statuses))
    query = f"SELECT DISTINCT user_id FROM orders WHERE status IN ({placeholders})"
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(query, tuple(statuses)) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

async def get_existing_user_ids(user_ids: list[int]):
    """Фильтрует список по наличию записей в таблице users."""
    if not user_ids:
        return []
    placeholders = ",".join(["?"] * len(user_ids))
    query = f"SELECT user_id FROM users WHERE user_id IN ({placeholders})"
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(query, tuple(user_ids)) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]


# ============================================================================
# RECURRING BROADCASTS (Повторяющиеся рассылки)
# ============================================================================

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
    last_sent_at: str = None,
    next_send_at: str = None,
    increment_sends: bool = True
):
    """Обновление статистики после отправки"""
    async with aiosqlite.connect(DB_NAME) as db:
        if increment_sends:
            await db.execute('''
                UPDATE recurring_broadcasts 
                SET last_sent_at = COALESCE(?, last_sent_at), 
                    next_send_at = COALESCE(?, next_send_at), 
                    total_sends = total_sends + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (last_sent_at, next_send_at, recurring_id))
        else:
            await db.execute('''
                UPDATE recurring_broadcasts 
                SET last_sent_at = COALESCE(?, last_sent_at), 
                    next_send_at = COALESCE(?, next_send_at),
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


async def get_recurring_stats(recurring_id: int):
    """Статистика рассылки"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT 
                COUNT(*) as total_sends,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_sends,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_sends,
                SUM(recipients_count) as total_recipients
            FROM recurring_send_log 
            WHERE recurring_id = ?
        ''', (recurring_id,)) as cursor:
            return await cursor.fetchone()


async def delete_recurring_broadcast(recurring_id: int):
    """Удаление рассылки и всех связанных данных"""
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
