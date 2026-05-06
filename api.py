"""
api.py — FastAPI REST API for Email Automation & Reminder System.

Endpoints:
  POST /contacts         — Create a contact
  GET  /contacts         — List all contacts
  POST /campaigns        — Create a campaign/template
  GET  /campaigns        — List all campaigns
  POST /reminders        — Schedule a reminder
  GET  /reminders        — List all reminders
  GET  /messages         — View message log (with filters)
  GET  /report           — Trigger and download CSV report
  GET  /stats            — Dashboard summary stats
  POST /test-send        — Send a test email immediately

Run with:
  uvicorn src.api:app --reload --port 8000
"""

import os
import sys
import uuid
import datetime
import json
import logging

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from typing import Optional

from src.db_init import get_connection, init_db
from src.renderer import render_email
from src.mailer import create_mailer_from_env
from src.reporter import generate_report

logger = logging.getLogger(__name__)

# Initialize DB on startup
init_db()

app = FastAPI(
    title="Email Automation & Reminder System",
    description="Schedule and send automated email reminders with recurring support.",
    version="1.0.0",
)


# ──────────────────────────────────────────────
# Pydantic Schemas
# ──────────────────────────────────────────────

class ContactCreate(BaseModel):
    name: str
    email: EmailStr
    timezone: str = "Asia/Kolkata"


class CampaignCreate(BaseModel):
    name: str
    subject: str
    body_md: str
    sender_name: str = "Automation System"
    sender_email: EmailStr = "noreply@example.com"


class ReminderCreate(BaseModel):
    title: str
    contact_id: str
    campaign_id: str
    start_at_utc: str          # ISO 8601, e.g. "2025-01-20T14:30:00"
    rrule: Optional[str] = None  # e.g. "FREQ=WEEKLY;BYDAY=MO,WE"


class TestSendRequest(BaseModel):
    to_email: EmailStr
    contact_name: str
    campaign_id: str
    dry_run: bool = True


# ──────────────────────────────────────────────
# Contacts
# ──────────────────────────────────────────────

@app.post("/contacts", tags=["Contacts"], summary="Create a new contact")
def create_contact(c: ContactCreate):
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM contacts WHERE email=?", (c.email,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail=f"Contact with email {c.email} already exists.")
        cid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO contacts(id,name,email,timezone) VALUES(?,?,?,?)",
            (cid, c.name, c.email, c.timezone)
        )
        conn.commit()
    return {"id": cid, "message": f"Contact '{c.name}' created."}


@app.get("/contacts", tags=["Contacts"], summary="List all contacts")
def list_contacts():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM contacts ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


@app.delete("/contacts/{contact_id}", tags=["Contacts"])
def unsubscribe_contact(contact_id: str):
    with get_connection() as conn:
        conn.execute("UPDATE contacts SET unsubscribed=1 WHERE id=?", (contact_id,))
        conn.commit()
    return {"message": "Contact unsubscribed."}


# ──────────────────────────────────────────────
# Campaigns / Templates
# ──────────────────────────────────────────────

@app.post("/campaigns", tags=["Campaigns"], summary="Create an email campaign/template")
def create_campaign(c: CampaignCreate):
    with get_connection() as conn:
        cid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO campaigns(id,name,subject,body_md,sender_name,sender_email) VALUES(?,?,?,?,?,?)",
            (cid, c.name, c.subject, c.body_md, c.sender_name, c.sender_email)
        )
        conn.commit()
    return {"id": cid, "message": f"Campaign '{c.name}' created."}


@app.get("/campaigns", tags=["Campaigns"])
def list_campaigns():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM campaigns ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────
# Reminders
# ──────────────────────────────────────────────

@app.post("/reminders", tags=["Reminders"], summary="Schedule a reminder")
def create_reminder(r: ReminderCreate):
    with get_connection() as conn:
        # Validate foreign keys
        contact = conn.execute("SELECT id FROM contacts WHERE id=?", (r.contact_id,)).fetchone()
        if not contact:
            raise HTTPException(status_code=404, detail=f"Contact {r.contact_id} not found.")
        campaign = conn.execute("SELECT id FROM campaigns WHERE id=?", (r.campaign_id,)).fetchone()
        if not campaign:
            raise HTTPException(status_code=404, detail=f"Campaign {r.campaign_id} not found.")

        rid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO reminders(id,title,contact_id,campaign_id,start_at_utc,rrule) VALUES(?,?,?,?,?,?)",
            (rid, r.title, r.contact_id, r.campaign_id, r.start_at_utc, r.rrule)
        )
        conn.commit()
    return {"id": rid, "message": f"Reminder '{r.title}' scheduled."}


@app.get("/reminders", tags=["Reminders"])
def list_reminders():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM reminders ORDER BY start_at_utc DESC").fetchall()
    return [dict(r) for r in rows]


@app.patch("/reminders/{reminder_id}/pause", tags=["Reminders"])
def pause_reminder(reminder_id: str):
    with get_connection() as conn:
        conn.execute("UPDATE reminders SET active=0 WHERE id=?", (reminder_id,))
        conn.commit()
    return {"message": "Reminder paused."}


@app.patch("/reminders/{reminder_id}/resume", tags=["Reminders"])
def resume_reminder(reminder_id: str):
    with get_connection() as conn:
        conn.execute("UPDATE reminders SET active=1 WHERE id=?", (reminder_id,))
        conn.commit()
    return {"message": "Reminder resumed."}


# ──────────────────────────────────────────────
# Messages Log
# ──────────────────────────────────────────────

@app.get("/messages", tags=["Messages"], summary="View message delivery log")
def list_messages(
    status: Optional[str] = Query(None, description="Filter by status: sent, failed, scheduled"),
    limit: int = Query(50, le=500),
):
    query = "SELECT * FROM messages"
    params = []
    if status:
        query += " WHERE status=?"
        params.append(status)
    query += " ORDER BY scheduled_at_utc DESC LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────
# Stats Dashboard
# ──────────────────────────────────────────────

@app.get("/stats", tags=["Analytics"], summary="Dashboard summary statistics")
def get_stats():
    with get_connection() as conn:
        total_contacts = conn.execute("SELECT COUNT(*) FROM contacts WHERE unsubscribed=0").fetchone()[0]
        total_campaigns = conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
        total_reminders = conn.execute("SELECT COUNT(*) FROM reminders WHERE active=1").fetchone()[0]
        msg_stats = conn.execute("""
            SELECT status, COUNT(*) as count FROM messages GROUP BY status
        """).fetchall()

    stats = {s['status']: s['count'] for s in msg_stats}
    total_msgs = sum(stats.values())
    sent = stats.get('sent', 0)

    return {
        "contacts_active": total_contacts,
        "campaigns": total_campaigns,
        "reminders_active": total_reminders,
        "messages_total": total_msgs,
        "messages_sent": sent,
        "messages_failed": stats.get('failed', 0),
        "messages_scheduled": stats.get('scheduled', 0),
        "delivery_rate_pct": round(sent / total_msgs * 100, 1) if total_msgs else 0.0,
    }


# ──────────────────────────────────────────────
# Test Send
# ──────────────────────────────────────────────

@app.post("/test-send", tags=["Testing"], summary="Send a test email immediately")
def test_send(req: TestSendRequest):
    with get_connection() as conn:
        campaign = conn.execute("SELECT * FROM campaigns WHERE id=?", (req.campaign_id,)).fetchone()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found.")
        campaign = dict(campaign)

    context = {
        "name": req.contact_name,
        "title": "Test Reminder",
        "scheduled_time": datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p'),
    }

    try:
        subject, body_html = render_email(campaign['subject'], campaign['body_md'], context)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Template error: {e}")

    mailer = create_mailer_from_env(dry_run=req.dry_run)
    result = mailer.send(
        from_name=campaign['sender_name'],
        from_email=campaign['sender_email'],
        to_email=req.to_email,
        subject=subject,
        html_body=body_html,
    )

    return {
        "ok": result['ok'],
        "dry_run": result['dry_run'],
        "sent_at": result['sent_at'],
        "subject": subject,
        "error": result.get('error'),
    }


# ──────────────────────────────────────────────
# Report Download
# ──────────────────────────────────────────────

@app.get("/report", tags=["Analytics"], summary="Generate and download CSV report")
def download_report():
    result = generate_report()
    return FileResponse(
        result['csv_path'],
        media_type='text/csv',
        filename=os.path.basename(result['csv_path'])
    )


# ──────────────────────────────────────────────
# Health Check
# ──────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "timestamp": datetime.datetime.utcnow().isoformat()}