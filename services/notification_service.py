from __future__ import annotations

from datetime import UTC, datetime

from services.id_service import IdService


class NotificationService:
    def __init__(self, data_service) -> None:
        self.data_service = data_service
        self.id_service = IdService()

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
        return record
