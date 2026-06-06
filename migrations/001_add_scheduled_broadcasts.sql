-- Create table for scheduled broadcasts
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
