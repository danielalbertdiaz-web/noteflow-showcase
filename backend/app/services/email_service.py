"""
Email service using SMTP (via the `emails` library).
Sends magic links and note status notifications.
"""

import logging
import os
from pathlib import Path
from typing import Optional

import emails
from emails.template import JinjaTemplate

from app.core.config import settings

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _load_template(filename: str) -> str:
    template_path = TEMPLATES_DIR / filename
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    # Inline fallback if template file is missing
    return "<html><body>{{ body }}</body></html>"


# Pre-load templates at import time
MAGIC_LINK_HTML = _load_template("magic_link_email.html")

NOTE_STATUS_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Note Status Update</title></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #1a73e8;">NoteFlow — Note Status Update</h2>
  <p>Hello,</p>
  <p>Your clinical note has been updated:</p>
  <div style="background: #f5f5f5; border-radius: 8px; padding: 16px; margin: 16px 0;">
    <strong>Note ID:</strong> {{ note_id }}<br>
    <strong>New Status:</strong> <span style="color: #1a73e8; font-weight: bold;">{{ status }}</span>
  </div>
  <p>Log in to NoteFlow to view and manage your notes.</p>
  <p style="color: #888; font-size: 12px;">
    This is an automated message from NoteFlow. Please do not reply.
  </p>
</body>
</html>
"""


class EmailService:
    """
    Sends transactional emails via SMTP.
    """

    def __init__(self) -> None:
        self._smtp_params = {
            "host": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "user": settings.SMTP_USER,
            "password": settings.SMTP_PASSWORD,
            "tls": True,
        }
        self._from_address = settings.SMTP_USER or "noreply@example.org"
        self._from_name = "NoteFlow"

    async def send_magic_link(self, to_email: str, token: str) -> None:
        """
        Send a magic-link login email.

        The token is embedded in a URL pointing to the APP_URL magic-link
        verification endpoint.
        """
        import asyncio

        magic_url = f"{settings.APP_URL}/auth/verify?token={token}"

        message = emails.Message(
            subject="Your NoteFlow Login Link",
            html=JinjaTemplate(MAGIC_LINK_HTML),
            mail_from=(self._from_name, self._from_address),
        )

        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: message.send(
                    to=to_email,
                    render={"magic_url": magic_url, "app_url": settings.APP_URL},
                    smtp=self._smtp_params,
                ),
            )
            if response.status_code not in (200, 250):
                logger.warning(
                    "Magic link email to %s returned status %s",
                    to_email, response.status_code
                )
            else:
                logger.info("Magic link email sent to %s", to_email)
        except Exception as exc:
            logger.error("Failed to send magic link email to %s: %s", to_email, exc)
            raise

    async def send_note_status_notification(
        self, to_email: str, note_id: str, status: str
    ) -> None:
        """
        Notify a clinician that their note status has changed.
        """
        import asyncio

        message = emails.Message(
            subject=f"NoteFlow — Note {status.capitalize()}",
            html=JinjaTemplate(NOTE_STATUS_HTML),
            mail_from=(self._from_name, self._from_address),
        )

        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: message.send(
                    to=to_email,
                    render={"note_id": note_id, "status": status},
                    smtp=self._smtp_params,
                ),
            )
            if response.status_code not in (200, 250):
                logger.warning(
                    "Status notification to %s returned status %s",
                    to_email, response.status_code
                )
            else:
                logger.info(
                    "Status notification sent to %s (note=%s, status=%s)",
                    to_email, note_id, status
                )
        except Exception as exc:
            logger.error(
                "Failed to send status notification to %s: %s", to_email, exc
            )
            raise
