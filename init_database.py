import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Таблица промокодов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promocodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            discount INTEGER NOT NULL,
            type TEXT DEFAULT 'percentage',
            max_uses INTEGER DEFAULT 0,
            current_uses INTEGER DEFAULT 0,
            valid_from DATETIME DEFAULT CURRENT_TIMESTAMP,
            valid_until DATETIME,
            active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
    """)
    
    # Таблица использования промокодов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promo_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            code TEXT NOT NULL,
            discount_amount INTEGER,
            order_id TEXT,
            product_name TEXT,
            used_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Индексы для быстрого поиска
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_promo_code ON promocodes(code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_promo_active ON promocodes(active)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_user ON promo_usage(user_id, code)")
    
    # Добавляем тестовые промокоды
    test_promos = [
        ('FREE10', 10, 'percentage', 0, 'Скидка 10% для всех'),
        ('SALE20', 20, 'percentage', 100, 'Скидка 20% - лимит 100 использований'),
        ('VIP30', 30, 'percentage', 50, 'VIP скидка 30%'),
    ]
    
    for code, discount, ptype, max_uses, desc in test_promos:
        try:
            cursor.execute("""
                INSERT INTO promocodes (code, discount, type, max_uses, description)
                VALUES (?, ?, ?, ?, ?)
            """, (code, discount, ptype, max_uses, desc))
        except sqlite3.IntegrityError:
            pass  # Промокод уже существует
    
    conn.commit()
    conn.close()
    print("✅ База данных создана!")

if __name__ == '__main__':
    init_db()
