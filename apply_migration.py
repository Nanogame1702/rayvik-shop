import argparse, sys
from pathlib import Path
import sqlite3

def find_one(pattern: str):
    items = sorted(Path.cwd().rglob(pattern), key=lambda p: len(str(p)))
    return items

def main():
    ap = argparse.ArgumentParser(description="Apply scheduled_broadcasts migration")
    ap.add_argument("--db", type=str, default=None, help="Path to shop_bot.db")
    ap.add_argument("--sql", type=str, default=None, help="Path to 001_add_scheduled_broadcasts.sql")
    args = ap.parse_args()

    candidates_db = []
    candidates_sql = []

    if args.db:
        db_path = Path(args.db).expanduser().resolve()
    else:
        candidates_db = find_one("shop_bot.db")
        if not candidates_db:
            print("❌ Не найден shop_bot.db. Укажите путь параметром --db")
            print("Подсказка: попробуйте запустить из корня проекта или укажите полный путь, например:")
            print("  py apply_migration.py --db D:/path/to/lunost_shop_bo/shop_bot.db --sql D:/path/to/migrations/001_add_scheduled_broadcasts.sql")
            sys.exit(2)
        db_path = candidates_db[0]

    if args.sql:
        sql_path = Path(args.sql).expanduser().resolve()
    else:
        candidates_sql = find_one("migrations/001_add_scheduled_broadcasts.sql")
        if not candidates_sql:
            print("❌ Не найден файл миграции migrations/001_add_scheduled_broadcasts.sql. Укажите путь параметром --sql")
            sys.exit(2)
        sql_path = candidates_sql[0]

    print(f"📄 SQL: {sql_path}")
    print(f"🗄  DB : {db_path}")

    if not db_path.exists():
        # Создадим пустую базу
        print("ℹ️ Файл базы не найден — будет создан автоматически.")
        db_path.parent.mkdir(parents=True, exist_ok=True)

    sql = sql_path.read_text(encoding="utf-8")
    with sqlite3.connect(db_path) as conn:
        conn.executescript(sql)
        conn.commit()
    print("✅ Migration applied successfully!")

    # Быстрая проверка
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scheduled_broadcasts'")
        ok = cur.fetchone() is not None
    print("🔎 Check table scheduled_broadcasts:", "OK" if ok else "NOT FOUND")

if __name__ == "__main__":
    main()