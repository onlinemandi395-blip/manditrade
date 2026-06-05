from __future__ import annotations

from datetime import UTC, datetime

from services.gmail_queue_service import GmailQueueService
from services.id_service import IdService


class NotificationService:
    def __init__(self, data_service) -> None:
        self.data_service = data_service
        self.id_service = IdService()
        self.gmail_queue_service = GmailQueueService(data_service)

    def create_notification(self, *, notification_type: str, title: str, message: str, metadata: dict | None = None) -> dict:
        record = {
            "notification_id": self.id_service.next("notification"),
            "type": notification_type,
            "title": title,
            "message": message,
            "metadata": metadata or {},
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.data_service._bootstrap_collection("notifications").append(record)
        to_email = str((metadata or {}).get("to_email", "")).strip()
        if self.gmail_queue_service.is_enabled() and to_email:
            self.gmail_queue_service.enqueue(
                to_email=to_email,
                subject=title,
                body=message,
            )
        return record
