from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from services.audit_service import AuditService


class OrderStateService:
    ALLOWED_TRANSITIONS = {
        "PROPOSED": {"COUNTER_PROPOSED", "MANUFACTURER_ACCEPTED", "PROCUREMENT_REQUIRED", "CANCELLED"},
        "COUNTER_PROPOSED": {"MANUFACTURER_ACCEPTED", "CANCELLED"},
        "MANUFACTURER_ACCEPTED": {"PROCUREMENT_REQUIRED", "READY_TO_CONFIRM", "CONFIRMED", "CANCELLED"},
        "PROCUREMENT_REQUIRED": {"READY_TO_CONFIRM", "CANCELLED"},
        "READY_TO_CONFIRM": {"CONFIRMED", "CANCELLED"},
        "CONFIRMED": {"DISPATCHED", "CANCELLED"},
        "DISPATCHED": {"DELIVERED"},
        "DELIVERED": {"CLOSED"},
        "CLOSED": set(),
        "CANCELLED": set(),
    }

    def __init__(self, audit_service: AuditService) -> None:
        self.audit_service = audit_service

    def can_transition(self, current_status: str, next_status: str) -> bool:
        if current_status == next_status:
            return True
        return next_status in self.ALLOWED_TRANSITIONS.get(current_status, set())

    def transition(self, order: dict[str, Any], next_status: str, actor: str, reason: str | None = None) -> dict[str, Any]:
        current = order.get("status", "PROPOSED")
        if not self.can_transition(current, next_status):
            raise ValueError(f"Illegal transition from {current} to {next_status}")
        if current == next_status:
            return order
        order["status"] = next_status
        order["updated_at"] = datetime.now(UTC).isoformat()
        order.setdefault("status_history", []).append(
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
