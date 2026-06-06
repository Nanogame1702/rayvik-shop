import sqlite3

conn = sqlite3.connect('shop_bot.db')
cur = conn.execute('SELECT id, scheduled_at_utc, status FROM scheduled_broadcasts ORDER BY id DESC LIMIT 5')
print("\nScheduled broadcasts:")
for row in cur.fetchall():
    print(f"ID: {row[0]}, Time: {row[1]}, Status: {row[2]}")

cur = conn.execute('SELECT COUNT(*) FROM users')
user_count = cur.fetchone()[0]
print(f"\nTotal users in database: {user_count}")

conn.close()
