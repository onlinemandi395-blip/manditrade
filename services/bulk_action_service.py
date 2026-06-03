from __future__ import annotations

from typing import Any


class BulkActionService:
    def __init__(
        self,
        *,
        notification_center_service,
        public_buyer_service,
        governance_service,
        gmail_service,
        audit_service=None,
    ) -> None:
        self.notification_center_service = notification_center_service
        self.public_buyer_service = public_buyer_service
        self.governance_service = governance_service
        self.gmail_service = gmail_service
        self.audit_service = audit_service

    def bulk_update_notifications(
        self,
        *,
        user,
        notification_ids: list[str],
        mark_read: bool | None = None,
        resolved: bool | None = None,
    ) -> dict[str, Any]:
        successes: list[str] = []
        failures: list[dict[str, str]] = []
        for notification_id in notification_ids:
            try:
                self._update_notification_status(
                    user,
                    notification_id,
                    mark_read=mark_read,
                    resolved=resolved,
                )
                successes.append(notification_id)
            except Exception as exc:  # noqa: BLE001
                failures.append({"notification_id": notification_id, "error": str(exc)})
        report = {
            "action": "resolve" if resolved else "read",
            "requested": len(notification_ids),
            "successes": successes,
            "failures": failures,
        }
        if self.audit_service:
            self.audit_service.log_event(
                "bulk_actions",
                getattr(user, "email", ""),
                {
                    "kind": "notification_status_update",
                    "role": getattr(user, "role", ""),
                    "requested": len(notification_ids),
                    "success_count": len(successes),
                    "failure_count": len(failures),
                },
            )
        return report

    def bulk_retry_failed_notifications(self, email_ids: list[str]) -> dict[str, Any]:
        successes: list[str] = []
        failures: list[dict[str, str]] = []
        for email_id in email_ids:
            try:
                self.gmail_service.retry_failed(email_id)
                successes.append(email_id)
            except Exception as exc:  # noqa: BLE001
                failures.append({"email_id": email_id, "error": str(exc)})
        return {
            "action": "retry_failed_notifications",
            "requested": len(email_ids),
            "successes": successes,
            "failures": failures,
        }

    def _update_notification_status(
        self,
        user,
        notification_id: str,
        *,
        mark_read: bool | None = None,
        resolved: bool | None = None,
    ) -> dict[str, Any]:
        if getattr(user, "role", "") == "public_buyer":
            buyer = self.public_buyer_service.get_by_email(getattr(user, "email", ""))
            if not buyer:
                raise ValueError("Public buyer profile not found.")
            return self.notification_center_service.update_public_status(
                buyer["public_buyer_id"],
                notification_id,
                mark_read=mark_read,
                resolved=resolved,
            )
        manufacturer_code = getattr(user, "manufacturer_code", "")
        if getattr(user, "role", "") == "platform_admin" and not manufacturer_code:
            for manufacturer in self.governance_service.list_manufacturers():
                try:
                    return self.notification_center_service.update_status(
                        manufacturer.get("manufacturer_code", ""),
                        notification_id,
                        mark_read=mark_read,
                        resolved=resolved,
                    )
                except ValueError:
                    continue
            raise ValueError(f"Notification not found: {notification_id}")
        if not manufacturer_code:
            raise ValueError("Notification owner context is missing.")
        return self.notification_center_service.update_status(
            manufacturer_code,
            notification_id,
            mark_read=mark_read,
            resolved=resolved,
        )
