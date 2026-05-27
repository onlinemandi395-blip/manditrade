from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class NotificationCenterService:
    def __init__(self, safe_drive_write_service, json_service, id_allocator_service, domain_paths_service) -> None:
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.id_allocator_service = id_allocator_service
        self.domain_paths = domain_paths_service

    def list_notifications(self, manufacturer_code: str) -> list[dict[str, Any]]:
        path = self.domain_paths.notifications_path(manufacturer_code)
        return self.json_service.read_json(path, {"schema_version": "2.0", "notifications": []}).get("notifications", [])

    def create_notification(
        self,
        manufacturer_code: str,
        *,
        user_id: str,
        notification_type: str,
        priority: str,
        title: str,
        message: str,
        source_type: str,
        source_id: str,
    ) -> dict[str, Any]:
        path = self.domain_paths.notifications_path(manufacturer_code)
        if not path.exists():
            self.safe_drive_write_service.replace_document(path, {"schema_version": "2.0", "notifications": []})
        notification = {
            "notification_id": self.id_allocator_service.allocate("notification"),
            "user_id": user_id,
            "type": notification_type,
            "priority": priority,
            "title": title,
            "message": message,
            "source_type": source_type,
            "source_id": source_id,
            "read": False,
            "resolved": False,
            "remind_later_at": "",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.safe_drive_write_service.append_record(path, "notifications", notification)
        return notification

    def update_status(self, manufacturer_code: str, notification_id: str, *, mark_read: bool | None = None, resolved: bool | None = None, remind_later_at: str | None = None) -> dict[str, Any]:
        path = self.domain_paths.notifications_path(manufacturer_code)
        updated: dict[str, Any] | None = None

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            nonlocal updated
            for item in payload.get("notifications", []):
                if item.get("notification_id") == notification_id:
                    if mark_read is not None:
                        item["read"] = mark_read
                    if resolved is not None:
                        item["resolved"] = resolved
                    if remind_later_at is not None:
                        item["remind_later_at"] = remind_later_at
                    updated = dict(item)
                    return payload
            raise ValueError(f"Notification not found: {notification_id}")

        self.safe_drive_write_service.mutate_json(path, mutator)
        return updated or {}
