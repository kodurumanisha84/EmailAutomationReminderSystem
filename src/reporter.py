"""
reporter.py — Generate CSV and summary reports from the messages table.

Outputs:
  - outputs/report_YYYYMMDD_HHMMSS.csv    (full message log)
  - outputs/summary_YYYYMMDD_HHMMSS.txt   (human-readable summary)
"""

import os
import csv
import logging
import datetime

from src.db_init import get_connection

logger = logging.getLogger(__name__)

OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'outputs')


def ensure_outputs_dir():
    os.makedirs(OUTPUTS_DIR, exist_ok=True)


def generate_report() -> dict:
    """
    Query all messages from DB, write CSV report and summary.

    Returns:
        dict with paths to generated files and stats
    """
    ensure_outputs_dir()
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_path = os.path.join(OUTPUTS_DIR, f'report_{timestamp}.csv')
    summary_path = os.path.join(OUTPUTS_DIR, f'summary_{timestamp}.txt')

    conn = get_connection()
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT
            m.id,
            m.contact_name,
            m.contact_email,
            m.subject,
            m.status,
            m.scheduled_at_utc,
            m.sent_at_utc,
            m.error,
            m.dry_run,
            c.name  AS campaign_name
        FROM messages m
        LEFT JOIN campaigns c ON c.id = m.campaign_id
        ORDER BY m.scheduled_at_utc DESC
    """).fetchall()
    conn.close()

    # ── Write CSV ──
    fieldnames = [
        'Message ID', 'Contact Name', 'Contact Email', 'Subject',
        'Status', 'Scheduled (UTC)', 'Sent (UTC)', 'Campaign', 'Error', 'Dry Run'
    ]

    counts = {'sent': 0, 'failed': 0, 'scheduled': 0, 'total': len(rows)}

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            status = row['status']
            counts[status] = counts.get(status, 0) + 1
            writer.writerow({
                'Message ID':      row['id'],
                'Contact Name':    row['contact_name'],
                'Contact Email':   row['contact_email'],
                'Subject':         row['subject'],
                'Status':          status.upper(),
                'Scheduled (UTC)': row['scheduled_at_utc'] or '',
                'Sent (UTC)':      row['sent_at_utc'] or '',
                'Campaign':        row['campaign_name'] or '',
                'Error':           row['error'] or '',
                'Dry Run':         'Yes' if row['dry_run'] else 'No',
            })

    # ── Write Summary ──
    sent_rate = (counts['sent'] / counts['total'] * 100) if counts['total'] else 0
    summary_lines = [
        "=" * 55,
        "  EMAIL AUTOMATION SYSTEM — SEND REPORT",
        "=" * 55,
        f"  Generated At   : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"  Total Messages : {counts['total']}",
        f"  ✓ Sent         : {counts.get('sent', 0)}",
        f"  ✗ Failed       : {counts.get('failed', 0)}",
        f"  ⏳ Scheduled   : {counts.get('scheduled', 0)}",
        f"  Delivery Rate  : {sent_rate:.1f}%",
        "=" * 55,
        f"  CSV Report     : {os.path.basename(csv_path)}",
        "=" * 55,
    ]

    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(summary_lines))

    for line in summary_lines:
        logger.info(line)

    print('\n'.join(summary_lines))

    return {
        'csv_path': csv_path,
        'summary_path': summary_path,
        'stats': counts,
    }


if __name__ == "__main__":
    generate_report()