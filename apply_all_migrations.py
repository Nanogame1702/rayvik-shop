"""
Применяет все SQL-миграции из папки migrations/
"""
import sqlite3
from pathlib import Path
import sys

def apply_all_migrations():
    db_path = Path("shop_bot.db")
    migrations_dir = Path("migrations")
    
    if not migrations_dir.exists():
        print("❌ Папка migrations/ не найдена")
        sys.exit(1)
    
    # Находим все .sql файлы
    sql_files = sorted(migrations_dir.glob("*.sql"))
    
    if not sql_files:
        print("❌ Нет SQL-миграций в папке migrations/")
        sys.exit(1)
    
    print(f"🔍 Найдено миграций: {len(sql_files)}")
    
    # Создаём/подключаемся к базе
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(db_path) as conn:
        for sql_file in sql_files:
            print(f"📄 Применяю: {sql_file.name}")
            sql = sql_file.read_text(encoding="utf-8")
            try:
                conn.executescript(sql)
                conn.commit()
                print(f"   ✅ {sql_file.name} применена")
            except Exception as e:
                print(f"   ⚠️  {sql_file.name} — возможно уже применена или ошибка: {e}")
    
    print("\n✅ Все миграции обработаны!")
    
    # Проверка промокода
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute("SELECT code, discount, max_uses FROM promocodes WHERE code = 'START10'")
        promo = cur.fetchone()
        if promo:
            print(f"🎁 Промокод добавлен: {promo[0]} (-{promo[1]}%, макс. {promo[2]} использований)")
        else:
            print("⚠️  Промокод START10 не найден")

if __name__ == "__main__":
    apply_all_migrations()
