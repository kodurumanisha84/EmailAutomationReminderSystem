"""
mailer.py — Email sending engine using smtplib (standard library).

Supports:
  - Gmail with App Password (TLS port 465 / STARTTLS port 587)
  - Dry-run mode (no real emails sent, just logged)
  - Per-message result dict with status, error, and timestamp
"""

import smtplib
import ssl
import logging
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

logger = logging.getLogger(__name__)


class Mailer:
    """
    Handles SMTP connection and email dispatch.

    Usage:
        mailer = Mailer(host, port, username, password, use_tls=True)
        result = mailer.send(from_name, from_email, to_email, subject, html_body)
        # result = {"ok": True/False, "sent_at": ..., "error": ...}
    """

    def __init__(
        self,
        host: str = "smtp.gmail.com",
        port: int = 465,
        username: str = "",
        password: str = "",
        use_tls: bool = True,       # SSL/TLS on port 465
        use_starttls: bool = False,  # STARTTLS on port 587
        dry_run: bool = False,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.use_starttls = use_starttls
        self.dry_run = dry_run

    def send(
        self,
        from_name: str,
        from_email: str,
        to_email: str,
        subject: str,
        html_body: str,
    ) -> dict:
        """
        Send a single HTML email.

        Returns:
            dict with keys: ok (bool), sent_at (str), error (str|None), dry_run (bool)
        """
        sent_at = datetime.datetime.utcnow().isoformat()

        # --- DRY RUN MODE: Skip actual sending ---
        if self.dry_run:
            logger.info(
                "[DRY RUN] Would send email | To: %s | Subject: %s",
                to_email, subject
            )
            return {
                "ok": True,
                "sent_at": sent_at,
                "error": None,
                "dry_run": True,
            }

        # --- Build MIME message ---
        msg = MIMEMultipart("alternative")
        msg["From"] = formataddr((from_name, from_email))
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["X-Mailer"] = "EmailAutomationSystem/1.0"
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # --- Send via SMTP ---
        try:
            if self.use_tls:
                # SSL/TLS connection (port 465)
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.host, self.port, context=context) as server:
                    server.login(self.username, self.password)
                    server.sendmail(from_email, to_email, msg.as_string())

            elif self.use_starttls:
                # STARTTLS connection (port 587)
                context = ssl.create_default_context()
                with smtplib.SMTP(self.host, self.port) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(self.username, self.password)
                    server.sendmail(from_email, to_email, msg.as_string())

            else:
                raise ValueError("Either use_tls or use_starttls must be True.")

            logger.info("Email sent successfully | To: %s | Subject: %s", to_email, subject)
            return {"ok": True, "sent_at": sent_at, "error": None, "dry_run": False}

        except smtplib.SMTPAuthenticationError:
            err = "SMTP Authentication failed. Check SMTP_USER and SMTP_PASS."
            logger.error("Auth error sending to %s: %s", to_email, err)
            return {"ok": False, "sent_at": sent_at, "error": err, "dry_run": False}

        except smtplib.SMTPRecipientsRefused:
            err = f"Recipient refused: {to_email}"
            logger.error(err)
            return {"ok": False, "sent_at": sent_at, "error": err, "dry_run": False}

        except smtplib.SMTPException as e:
            err = f"SMTP error: {str(e)}"
            logger.error("SMTP error sending to %s: %s", to_email, err)
            return {"ok": False, "sent_at": sent_at, "error": err, "dry_run": False}

        except Exception as e:
            err = f"Unexpected error: {str(e)}"
            logger.error("Unexpected error sending to %s: %s", to_email, err)
            return {"ok": False, "sent_at": sent_at, "error": err, "dry_run": False}


# -------------------------------------------------------------------
# Factory function — reads config from environment variables
# -------------------------------------------------------------------
def create_mailer_from_env(dry_run: bool = False) -> Mailer:
    """
    Create a Mailer instance using environment variables.

    Required env vars:
        SMTP_HOST   (default: smtp.gmail.com)
        SMTP_PORT   (default: 465)
        SMTP_USER   — your Gmail address
        SMTP_PASS   — Gmail App Password (not your regular password)

    Gmail App Password setup:
        1. Go to Google Account → Security → 2-Step Verification
        2. At the bottom → App passwords
        3. Generate a 16-char password for "Mail"
    """
    import os
    return Mailer(
        host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        port=int(os.getenv("SMTP_PORT", "465")),
        username=os.getenv("SMTP_USER", ""),
        password=os.getenv("SMTP_PASS", ""),
        use_tls=True,
        dry_run=dry_run,
    )