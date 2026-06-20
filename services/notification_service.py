from __future__ import annotations

from datetime import UTC, datetime

from services.gmail_queue_service import GmailQueueService
from services.id_service import IdService


class NotificationService:
    def __init__(self, data_service) -> None:
        self.data_service = data_service
        self.id_service = IdService()
        self.gmail_queue_service = GmailQueueService(data_service)

    def create_notification(
        self,
        *,
        to_email: str,
        title: str,
        message: str,
        event_type: str,
        to_role: str = "",
        recipients: list[str] | None = None,
        owner_email: str = "",
        source_entity: str | None = None,
        source_id: str | None = None,
        metadata: dict | None = None,
        created_by: str = "",
    ) -> dict:
        normalized_to_email = str(to_email or "").strip().lower()
        recipient_rows = [str(email or "").strip().lower() for email in (recipients or []) if str(email or "").strip()]
        record = {
            "notification_id": self.id_service.next("notification"),
            "event_type": event_type,
            "title": title,
            "message": message,
            "to_email": normalized_to_email,
            "to_role": str(to_role or "").strip().lower(),
            "recipients": recipient_rows,
            "owner_email": str(owner_email or "").strip().lower(),
            "source_entity": str(source_entity or "").strip(),
            "source_id": str(source_id or "").strip(),
            "status": "UNREAD",
            "created_at": datetime.now(UTC).isoformat(),
            "created_by": created_by,
            "metadata": metadata or {},
        }
        self.data_service._bootstrap_collection("notifications").append(record)
        if self.gmail_queue_service.is_enabled() and normalized_to_email:
            self.gmail_queue_service.enqueue(
                to_email=normalized_to_email,
                subject=title,
                body=message,
                notification_id=record["notification_id"],
            )
        return record

    def _is_visible_to_user(self, record: dict, user_email: str, role: str) -> bool:
        normalized_email = str(user_email or "").strip().lower()
        normalized_role = str(role or "").strip().lower()
        if normalized_role == "platform_admin":
            return True
        to_email = str(record.get("to_email", "")).strip().lower()
        owner_email = str(record.get("owner_email", "")).strip().lower()
        recipients = {str(email or "").strip().lower() for email in (record.get("recipients", []) or []) if str(email or "").strip()}
        to_role = str(record.get("to_role", "")).strip().lower()
        if normalized_email and normalized_email == to_email:
            return True
        if normalized_email and normalized_email in recipients:
            return True
        if normalized_role == "mahajan" and to_role == "mahajan" and owner_email == normalized_email:
            return True
        return False

    def list_notifications_for_user(self, user_email: str, role: str) -> list[dict]:
        rows = self.data_service.get_collection_ref("notifications")
        return [row for row in rows if self._is_visible_to_user(row, user_email, role)]

    def mark_read(self, notification_id: str, user_email: str, role: str) -> bool:
        rows = self.data_service.get_collection_ref("notifications")
        for row in rows:
            if str(row.get("notification_id", "")).strip() != str(notification_id).strip():
                continue
            if not self._is_visible_to_user(row, user_email, role):
                return False
            row["status"] = "READ"
            row["read_at"] = datetime.now(UTC).isoformat()
            row["read_by"] = str(user_email or "").strip().lower()
            return True
        return False

    def mark_all_read_for_user(self, user_email: str, role: str) -> int:
        rows = self.data_service.get_collection_ref("notifications")
        updated = 0
        for row in rows:
            if not self._is_visible_to_user(row, user_email, role):
                continue
            if str(row.get("status", "UNREAD")).upper() == "READ":
                continue
            row["status"] = "READ"
            row["read_at"] = datetime.now(UTC).isoformat()
            row["read_by"] = str(user_email or "").strip().lower()
            updated += 1
        return updated
