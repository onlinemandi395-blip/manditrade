from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from services.audit_service import AuditService


class OrderStateService:
    ALLOWED_TRANSITIONS = {
        "PLACED": {"VALIDATED", "FAILED", "CANCELLED"},
        "VALIDATED": {"CONFIRMED", "PROCUREMENT_REQUIRED", "FAILED", "CANCELLED"},
        "CONFIRMED": {"AGREEMENT_PENDING", "FAILED", "DISPUTED", "CANCELLED"},
        "PROCUREMENT_REQUIRED": {"AGREEMENT_PENDING", "FAILED", "CANCELLED"},
        "AGREEMENT_PENDING": {"ADVANCE_PENDING", "CANCELLED", "FAILED"},
        "ADVANCE_PENDING": {"DISPATCH_READY", "FAILED", "DISPUTED"},
        "DISPATCH_READY": {"DISPATCHED", "FAILED"},
        "DISPATCHED": {"DELIVERED", "DISPUTED"},
        "DELIVERED": {"CLOSED", "DISPUTED"},
        "CLOSED": set(),
        "CANCELLED": set(),
        "FAILED": set(),
        "DISPUTED": {"CLOSED"},
    }

    def __init__(self, audit_service: AuditService) -> None:
        self.audit_service = audit_service

    def can_transition(self, current_status: str, next_status: str) -> bool:
        return next_status in self.ALLOWED_TRANSITIONS.get(current_status, set())

    def transition(self, order: dict[str, Any], next_status: str, actor: str, reason: str | None = None) -> dict[str, Any]:
        current = order.get("status", "PLACED")
        if not self.can_transition(current, next_status):
            raise ValueError(f"Illegal transition from {current} to {next_status}")
        order["status"] = next_status
        order["updated_at"] = datetime.now(UTC).isoformat()
        timeline = order.setdefault("status_history", [])
        timeline.append(
            {
                "from": current,
                "to": next_status,
                "actor": actor,
                "reason": reason or "",
                "timestamp": order["updated_at"],
            }
        )
        self.audit_service.log_event(
            "order_status_changed",
            actor=actor,
            details={"order_id": order.get("order_id", ""), "from": current, "to": next_status, "reason": reason or ""},
        )
        return order
