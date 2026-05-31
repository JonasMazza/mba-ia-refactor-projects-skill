"""Email notification service.

Reads SMTP credentials from `config.settings` — never hardcoded.
When `settings.NOTIFICATIONS_ENABLED` is false (default in dev/test),
notifications are logged but no real SMTP connection is opened.
"""
import logging
import smtplib
from datetime import datetime, timezone

from config.settings import settings

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self):
        # In-memory log of dispatched notifications — useful for dev UI
        # and for the /notifications endpoint per user.
        self.notifications: list[dict] = []

    # --- transport -----------------------------------------------------

    def send_email(self, to: str, subject: str, body: str) -> bool:
        if not settings.NOTIFICATIONS_ENABLED:
            logger.info("notifications disabled — would send to=%s subject=%r", to, subject)
            return True

        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning("SMTP credentials missing — skipping email to %s", to)
            return False

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                message = f"Subject: {subject}\n\n{body}"
                server.sendmail(settings.SMTP_USER, to, message)
            logger.info("email sent to=%s", to)
            return True
        except smtplib.SMTPException:
            logger.exception("failed to send email to %s", to)
            return False

    # --- domain notifications -----------------------------------------

    def notify_task_assigned(self, user, task) -> None:
        subject = f"Nova task atribuída: {task.title}"
        body = (
            f"Olá {user.name},\n\nA task '{task.title}' foi atribuída a você.\n\n"
            f"Prioridade: {task.priority}\nStatus: {task.status}"
        )
        self.send_email(user.email, subject, body)
        self.notifications.append({
            "type": "task_assigned",
            "user_id": user.id,
            "task_id": task.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def notify_task_overdue(self, user, task) -> None:
        subject = f"Task atrasada: {task.title}"
        body = (
            f"Olá {user.name},\n\nA task '{task.title}' está atrasada!\n\n"
            f"Data limite: {task.due_date}"
        )
        self.send_email(user.email, subject, body)
        self.notifications.append({
            "type": "task_overdue",
            "user_id": user.id,
            "task_id": task.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_notifications(self, user_id: int) -> list[dict]:
        return [n for n in self.notifications if n["user_id"] == user_id]


# Module-level singleton — imported by services that need to notify.
notification_service = NotificationService()
