import os
import csv
import json
import uuid
import logging
import datetime
import time
import pytz
import sys

from dateutil.rrule import rrulestr

# Ensure src/ is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.renderer import render_email
from src.mailer import create_mailer_from_env
from src.db_init import get_connection, init_db

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# ──────────────────────────────────────────────
# Data Loading
# ──────────────────────────────────────────────

def load_contacts() -> dict:
    path = os.path.join(DATA_DIR, 'contacts.csv')
    contacts = {}
    if not os.path.exists(path): return {}
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            contacts[row['id']] = {
                'id': row['id'], 'name': row['name'], 'email': row['email'],
                'timezone': row.get('timezone', 'Asia/Kolkata'),
                'unsubscribed': row.get('unsubscribed', 'false').lower() == 'true',
            }
    return contacts

def load_campaigns() -> dict:
    path = os.path.join(DATA_DIR, 'campaigns.json')
    if not os.path.exists(path): return {}
    with open(path, encoding='utf-8') as f:
        items = json.load(f)
    return {c['id']: c for c in items}

def load_reminders() -> list:
    path = os.path.join(DATA_DIR, 'reminders.csv')
    reminders = []
    if not os.path.exists(path): return []
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('active', 'true').lower() == 'true':
                reminders.append(row)
    return reminders

# ──────────────────────────────────────────────
# Database Synchronization (Matches your db_init.py)
# ──────────────────────────────────────────────

def sync_data_to_db(contacts, campaigns, reminders, conn):
    cur = conn.cursor()
    
    # Sync Contacts
    for c_id, c in contacts.items():
        cur.execute("""
            INSERT INTO contacts (id, name, email, timezone, unsubscribed) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET name=excluded.name, email=excluded.email, 
                                          timezone=excluded.timezone, unsubscribed=excluded.unsubscribed
        """, (c_id, c['name'], c['email'], c['timezone'], 1 if c['unsubscribed'] else 0))

    # Sync Campaigns (Matches 'body_md' and 'name' from your SQL)
    for camp_id, camp in campaigns.items():
        cur.execute("""
            INSERT INTO campaigns (id, name, subject, body_md) VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET name=excluded.name, subject=excluded.subject, body_md=excluded.body_md
        """, (camp_id, camp.get('name', 'Campaign'), camp['subject'], camp.get('body_md', '')))

    # Sync Reminders
    for rem in reminders:
        cur.execute("""
            INSERT INTO reminders (id, title, contact_id, campaign_id, start_at_utc, rrule, active) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET title=excluded.title, rrule=excluded.rrule, active=excluded.active
        """, (rem['id'], rem['title'], rem['contact_id'], rem['campaign_id'], 
              rem['start_at_utc'], rem.get('rrule', ''), 1 if rem.get('active', 'true').lower() == 'true' else 0))
    conn.commit()

# ──────────────────────────────────────────────
# Time & Logic
# ──────────────────────────────────────────────

def _parse_utc_datetime(dt_str: str) -> datetime.datetime:
    if not dt_str: return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ'):
        try:
            d = datetime.datetime.strptime(dt_str.strip(), fmt)
            return pytz.UTC.localize(d) if d.tzinfo is None else d.astimezone(pytz.UTC)
        except ValueError: continue
    return None

def get_next_fire(reminder: dict, now_utc: datetime.datetime) -> datetime.datetime | None:
    start = _parse_utc_datetime(reminder['start_at_utc'])
    if not start: return None
    rrule_str = reminder.get('rrule', '').strip()
    last_str = reminder.get('last_fired_at', '').strip()
    last = _parse_utc_datetime(last_str)

    if rrule_str:
        rule = rrulestr(rrule_str, dtstart=start.replace(tzinfo=None))
        after_dt = last.replace(tzinfo=None) if last else start.replace(tzinfo=None) - datetime.timedelta(seconds=1)
        next_naive = rule.after(after_dt, inc=False)
        if not next_naive: return None
        next_fire = pytz.UTC.localize(next_naive)
    else:
        if last: return None
        next_fire = start

    if next_fire <= now_utc + datetime.timedelta(seconds=60):
        return next_fire
    return None

def plan_messages(contacts: dict, campaigns: dict, reminders: list, now_utc: datetime.datetime, conn) -> int:
    cur = conn.cursor()
    planned = 0
    for reminder in reminders:
        contact = contacts.get(reminder['contact_id'])
        campaign = campaigns.get(reminder['campaign_id'])
        if not contact or not campaign or contact['unsubscribed']: continue

        next_fire = get_next_fire(reminder, now_utc)
        if not next_fire: continue

        fire_str = next_fire.isoformat()
        existing = cur.execute("SELECT id FROM messages WHERE reminder_id=? AND scheduled_at_utc=?", 
                               (reminder['id'], fire_str)).fetchone()
        if existing: continue

        tz = pytz.timezone(contact['timezone'])
        local_time_str = next_fire.astimezone(tz).strftime('%B %d, %Y at %I:%M %p')
        context = {'name': contact['name'], 'title': reminder.get('title', 'Reminder'), 'scheduled_time': local_time_str}

        try:
            # Note: Using body_md to match your campaign loading
            subject, body_html = render_email(campaign['subject'], campaign.get('body_md', ''), context)
        except Exception as e:
            logger.error(f"Render error: {e}")
            continue

        msg_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO messages(id, reminder_id, campaign_id, contact_id, contact_name, contact_email,
                                 subject, body_html, scheduled_at_utc, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'scheduled')
        """, (msg_id, reminder['id'], campaign['id'], contact['id'],
              contact['name'], contact['email'], subject, body_html, fire_str))
        planned += 1
    conn.commit()
    return planned

def dispatch_messages(mailer, now_utc: datetime.datetime, conn) -> tuple[int, int]:
    cur = conn.cursor()
    due = cur.execute("SELECT id, contact_email, contact_name, subject, body_html FROM messages WHERE status='scheduled' AND scheduled_at_utc <= ?", 
                      (now_utc.isoformat(),)).fetchall()
    sent = failed = 0
    for row in due:
        result = mailer.send(
            from_name="Reminder System",
            from_email=os.getenv("SMTP_USER", "noreply@example.com"),
            to_email=row['contact_email'],
            subject=row['subject'],
            html_body=row['body_html'],
        )
        status = 'sent' if result['ok'] else 'failed'
        cur.execute("UPDATE messages SET status=?, sent_at_utc=? WHERE id=?", 
                    (status, datetime.datetime.now(datetime.timezone.utc).isoformat(), row['id']))
        if result['ok']: sent += 1
        else: failed += 1
    conn.commit()
    return sent, failed

def run_scheduler(dry_run: bool = True, tick_seconds: int = 15):
    init_db()
    mailer = create_mailer_from_env(dry_run=dry_run)
    logger.info(f"Scheduler running. Mode: {'DRY RUN' if dry_run else 'LIVE'}")

    while True:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        contacts = load_contacts()
        campaigns = load_campaigns()
        reminders = load_reminders()

        with get_connection() as conn:
            sync_data_to_db(contacts, campaigns, reminders, conn)
            p = plan_messages(contacts, campaigns, reminders, now_utc, conn)
            s, f = dispatch_messages(mailer, now_utc, conn)
            if p or s or f:
                logger.info(f"Cycle: Planned {p}, Sent {s}, Failed {f}")
        time.sleep(tick_seconds)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    run_scheduler(dry_run=not args.live)