"""
db_init.py — Initialize SQLite database with full schema
Run once before starting the application.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'email_automation.db')


def get_connection():
    """Return a SQLite connection with row_factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS contacts (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            email       TEXT UNIQUE NOT NULL,
            timezone    TEXT DEFAULT 'Asia/Kolkata',
            unsubscribed INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS campaigns (
            id            TEXT PRIMARY KEY,
            name          TEXT NOT NULL,
            subject       TEXT NOT NULL,
            body_md       TEXT NOT NULL,
            sender_name   TEXT DEFAULT 'Automation System',
            sender_email  TEXT DEFAULT 'noreply@example.com',
            created_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS reminders (
            id               TEXT PRIMARY KEY,
            title            TEXT NOT NULL,
            contact_id       TEXT REFERENCES contacts(id),
            campaign_id      TEXT REFERENCES campaigns(id),
            start_at_utc     TEXT NOT NULL,
            rrule            TEXT,
            active           INTEGER DEFAULT 1,
            last_fired_at    TEXT,
            created_at       TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS messages (
            id                  TEXT PRIMARY KEY,
            reminder_id         TEXT REFERENCES reminders(id),
            campaign_id         TEXT,
            contact_id          TEXT,
            contact_name        TEXT,
            contact_email       TEXT,
            subject             TEXT,
            body_html           TEXT,
            scheduled_at_utc    TEXT,
            sent_at_utc         TEXT,
            status              TEXT DEFAULT 'scheduled',
            error               TEXT,
            dry_run             INTEGER DEFAULT 0,
            created_at          TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status);
        CREATE INDEX IF NOT EXISTS idx_messages_scheduled ON messages(scheduled_at_utc, status);
        CREATE INDEX IF NOT EXISTS idx_reminders_active ON reminders(active);
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Database initialized at: {os.path.abspath(DB_PATH)}")


if __name__ == "__main__":
    init_db()