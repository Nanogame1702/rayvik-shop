import sqlite3

conn = sqlite3.connect('shop_bot.db')

# Сбрасываем застрявшую задачу
conn.execute("UPDATE scheduled_broadcasts SET status = 'failed' WHERE status = 'sending'")
conn.commit()

print("Reset stuck tasks")

# Показываем текущие задачи
cur = conn.execute('SELECT id, scheduled_at_utc, status FROM scheduled_broadcasts ORDER BY id DESC LIMIT 5')
print("\nCurrent scheduled broadcasts:")
for row in cur.fetchall():
    print(f"ID: {row[0]}, Time: {row[1]}, Status: {row[2]}")

conn.close()
