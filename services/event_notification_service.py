from __future__ import annotations

from typing import Any

from utils.deep_links import build_deep_link_target


class EventNotificationService:
    DEFAULT_RULE = {"in_app": True, "gmail": True, "severity": "MEDIUM"}

    def __init__(self, *, notification_center_service, gmail_service, governance_service, public_buyer_service, notification_rules: dict[str, Any] | None = None) -> None:
        self.notification_center_service = notification_center_service
        self.gmail_service = gmail_service
        self.governance_service = governance_service
        self.public_buyer_service = public_buyer_service
        self.notification_rules = (notification_rules or {}).get("events", notification_rules or {})

    def emit(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        rule = {**self.DEFAULT_RULE, **dict(self.notification_rules.get(event_type, {}))}
        recipients = self._resolve_recipients(event_type, payload)
        created = {"in_app": [], "emails": []}
        deep_link = build_deep_link_target(payload.get("entity_type", payload.get("source_type", "")), payload.get("entity_id", payload.get("source_id", "")))
        for recipient in recipients:
            title = str(payload.get("title") or event_type.replace("_", " ").title())
            message = str(payload.get("message") or title)
            if rule.get("in_app", True):
                created["in_app"].append(
                    self._create_notification(recipient, event_type, title, message, payload, deep_link, severity=str(rule.get("severity", "MEDIUM")))
                )
            if rule.get("gmail", True) and recipient.get("email"):
                self.gmail_service.enqueue_message(
                    recipient["email"],
                    title,
                    message,
                    event_type,
                    deep_link=deep_link.get("route", ""),
                    metadata={
                        "entity_type": payload.get("entity_type", payload.get("source_type", "")),
                        "entity_id": payload.get("entity_id", payload.get("source_id", "")),
                        "recipient_role": recipient.get("role", ""),
                    },
                )
                created["emails"].append(recipient["email"])
        return created

    def _create_notification(self, recipient: dict[str, Any], event_type: str, title: str, message: str, payload: dict[str, Any], deep_link: dict[str, str], *, severity: str) -> dict[str, Any]:
        base_kwargs = {
            "user_id": recipient.get("user_id", ""),
            "notification_type": event_type,
            "priority": severity,
            "title": title,
            "message": message,
            "source_type": payload.get("entity_type", payload.get("source_type", "")),
            "source_id": payload.get("entity_id", payload.get("source_id", "")),
            "source_route": deep_link.get("route", ""),
            "thumbnail_url": payload.get("thumbnail_url", ""),
            "severity": severity,
            "recipient_role": recipient.get("role", ""),
        }
        if recipient.get("role") == "public_buyer":
            return self.notification_center_service.create_public_notification(recipient["owner_id"], **base_kwargs)
        return self.notification_center_service.create_notification(recipient["owner_id"], **base_kwargs)

    def _resolve_recipients(self, event_type: str, payload: dict[str, Any]) -> list[dict[str, str]]:
        manufacturer_code = str(payload.get("manufacturer_code", "")).strip()
        manufacturer_email = str(payload.get("manufacturer_email", "")).strip().lower()
        mahajan_id = str(payload.get("mahajan_id", "")).strip()
        public_buyer_id = str(payload.get("public_buyer_id", "")).strip()
        public_buyer_email = str(payload.get("public_buyer_email", "")).strip().lower()
        worker_id = str(payload.get("worker_id", "")).strip()
        worker_email = str(payload.get("worker_email", "")).strip().lower()
        admin_email = str(payload.get("admin_email", "")).strip().lower()
        recipients: list[dict[str, str]] = []
        if event_type in {"PRODUCT_APPROVAL_REQUESTED", "PAYMENT_DISPUTE", "FAILED_WORKFLOW", "SYSTEM_HEALTH_ALERT", "COMMISSION_DUE", "MANUFACTURER_CREATED", "MANUFACTURER_UPDATED", "MAHAJAN_INVITED", "MAHAJAN_ONBOARDED"}:
            recipients.append({"role": "platform_admin", "owner_id": manufacturer_code or "PLATFORM_ADMIN", "user_id": admin_email or "PLATFORM_ADMIN", "email": admin_email})
        if event_type in {"PRODUCT_APPROVED", "PRODUCT_REJECTED", "MARKETPLACE_ORDER_CREATED", "MANDI_ORDER_CREATED", "SUPPLY_ORDER_CREATED", "PAYMENT_SUBMITTED", "PAYMENT_VERIFIED", "LOGISTICS_UPDATED", "JOB_APPLICATION_RECEIVED", "RAW_MATERIAL_CREATED", "RAW_MATERIAL_UPDATED", "ARCHIVED"} and manufacturer_code:
            recipients.append({"role": "manufacturer", "owner_id": manufacturer_code, "user_id": manufacturer_code, "email": manufacturer_email})
        if event_type in {"SUPPLY_ORDER_ASSIGNED", "SUPPLY_ORDER_CONFIRMED", "PAYMENT_UPDATED", "LOGISTICS_UPDATED", "RAW_MATERIAL_LOW_STOCK"} and mahajan_id:
            mahajan = self.governance_service.get_mahajan(mahajan_id) or {}
            recipients.append({"role": "mahajan", "owner_id": manufacturer_code or mahajan_id, "user_id": mahajan_id, "email": str(mahajan.get("email", "")).strip().lower()})
        if event_type in {"MARKETPLACE_ORDER_CREATED", "PAYMENT_INSTRUCTION", "PAYMENT_VERIFIED", "PAYMENT_REJECTED", "ORDER_DISPATCHED", "DELIVERY_COMPLETED"} and public_buyer_id:
            recipients.append({"role": "public_buyer", "owner_id": public_buyer_id, "user_id": public_buyer_email or public_buyer_id, "email": public_buyer_email})
        if event_type in {"JOB_APPLICATION_UPDATE", "JOB_ACCEPTED", "JOB_REJECTED", "TASK_UPDATE"} and worker_id:
            recipients.append({"role": "worker", "owner_id": manufacturer_code or worker_id, "user_id": worker_id, "email": worker_email})
        return [recipient for recipient in recipients if recipient.get("owner_id")]
