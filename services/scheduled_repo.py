import aiosqlite
from typing import Optional, List

from database import DB_NAME

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS scheduled_broadcasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audience TEXT NOT NULL CHECK(audience IN ('all','buyers')),
    text TEXT NOT NULL,
    parse_mode TEXT DEFAULT 'HTML',
    keyboard_json TEXT NULL,
    scheduled_at_utc TEXT NOT NULL,
    tz TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','sending','done','cancelled','failed')),
    created_by INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    sent_total INTEGER DEFAULT 0,
    sent_ok INTEGER DEFAULT 0,
    sent_failed INTEGER DEFAULT 0,
    last_error TEXT NULL
);
CREATE INDEX IF NOT EXISTS idx_sched_status_time ON scheduled_broadcasts(status, scheduled_at_utc);
"""

async def ensure_schema():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.executescript(CREATE_SQL)
        await db.commit()

async def create(audience: str, text: str, parse_mode: str, keyboard_json: str, scheduled_at_utc: str, tz: str, created_by: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "INSERT INTO scheduled_broadcasts(audience,text,parse_mode,keyboard_json,scheduled_at_utc,tz,created_by) VALUES(?,?,?,?,?,?,?)",
            (audience, text, parse_mode, keyboard_json, scheduled_at_utc, tz, created_by),
        )
        await db.commit()
        return cur.lastrowid

async def list_upcoming(limit: int = 20) -> List[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT id,audience,text,scheduled_at_utc,tz,status FROM scheduled_broadcasts WHERE status IN ('pending','sending') ORDER BY scheduled_at_utc LIMIT ?", (limit,))
        rows = await cur.fetchall()
        return [{"id": r[0], "audience": r[1], "text": r[2], "scheduled_at_utc": r[3], "tz": r[4], "status": r[5]} for r in rows]

async def get_due(now_utc_iso: str, limit: int = 3) -> List[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT id,audience,text,parse_mode,keyboard_json,scheduled_at_utc,tz FROM scheduled_broadcasts WHERE status='pending' AND scheduled_at_utc <= ? ORDER BY scheduled_at_utc LIMIT ?", (now_utc_iso, limit))
        rows = await cur.fetchall()
        return [
            {"id": r[0], "audience": r[1], "text": r[2], "parse_mode": r[3], "keyboard_json": r[4], "scheduled_at_utc": r[5], "tz": r[6]}
            for r in rows
        ]

async def mark_status(task_id: int, status: str, last_error: Optional[str] = None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE scheduled_broadcasts SET status=?, last_error=? WHERE id=?", (status, last_error, task_id))
        await db.commit()

async def update_stats(task_id: int, total: int, ok: int, failed: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE scheduled_broadcasts SET sent_total=?, sent_ok=?, sent_failed=? WHERE id=?", (total, ok, failed, task_id))
        await db.commit()

async def cancel(task_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE scheduled_broadcasts SET status='cancelled' WHERE id=?", (task_id,))
        await db.commit()

async def get_by_id(task_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT id,audience,text,parse_mode,keyboard_json,scheduled_at_utc,tz,status FROM scheduled_broadcasts WHERE id=?", (task_id,))
        row = await cur.fetchone()
        if not row:
            return None
        return {"id": row[0], "audience": row[1], "text": row[2], "parse_mode": row[3], "keyboard_json": row[4], "scheduled_at_utc": row[5], "tz": row[6], "status": row[7]}
