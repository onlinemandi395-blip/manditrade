from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from constants.statuses import STATUS_DISPUTED, STATUS_PENDING, STATUS_REJECTED, STATUS_RESOLVED


class DisputeService:
    def __init__(self, *, governance_service, id_allocator_service, settlement_service, event_notification_service=None) -> None:
        self.governance_service = governance_service
        self.id_allocator_service = id_allocator_service
        self.settlement_service = settlement_service
        self.event_notification_service = event_notification_service

    def create_dispute(
        self,
        *,
        related_transaction_id: str,
        related_order_id: str,
        raised_by_role: str,
        raised_by_id: str,
        reason: str,
        evidence_refs: list[str] | None = None,
    ) -> dict[str, Any]:
        dispute = self.governance_service.upsert_dispute(
            {
                "dispute_id": self.id_allocator_service.allocate("dispute"),
                "related_transaction_id": related_transaction_id,
                "related_order_id": related_order_id,
                "raised_by_role": raised_by_role,
                "raised_by_id": raised_by_id,
                "reason": reason,
                "evidence_refs": list(evidence_refs or []),
                "status": "OPEN",
                "resolution_note": "",
                "created_at": datetime.now(UTC).isoformat(),
                "created_by": raised_by_id,
                "updated_by": raised_by_id,
                "version": 1,
            }
        )
        transaction = self.governance_service.get_financial_transaction(related_transaction_id)
        if transaction:
            transaction["status"] = STATUS_DISPUTED
            transaction["updated_by"] = raised_by_id
            self.governance_service.upsert_financial_transaction(transaction)
        if self.event_notification_service:
            self.event_notification_service.emit(
                "DISPUTE_CREATED",
                {
                    "entity_type": "DISPUTE",
                    "entity_id": dispute["dispute_id"],
                    "title": "Dispute opened",
                    "message": f"Dispute opened for {related_order_id or related_transaction_id}.",
                    "manufacturer_code": raised_by_id if raised_by_role == "manufacturer" else "",
                },
            )
        return dispute

    def resolve_dispute(self, *, dispute_id: str, resolution_note: str, actor_id: str, approved: bool = True) -> dict[str, Any]:
        dispute = self.governance_service.get_dispute(dispute_id)
        if not dispute:
            raise ValueError("Dispute not found.")
        dispute["status"] = STATUS_RESOLVED if approved else STATUS_REJECTED
        dispute["resolution_note"] = resolution_note
        dispute["updated_by"] = actor_id
        saved = self.governance_service.upsert_dispute(dispute)
        transaction = self.governance_service.get_financial_transaction(saved.get("related_transaction_id", ""))
        if transaction:
            transaction["status"] = STATUS_PENDING if approved else transaction.get("status", STATUS_PENDING)
            transaction["updated_by"] = actor_id
            self.governance_service.upsert_financial_transaction(transaction)
        if self.event_notification_service:
            self.event_notification_service.emit(
                "DISPUTE_RESOLVED",
                {
                    "entity_type": "DISPUTE",
                    "entity_id": saved["dispute_id"],
                    "title": "Dispute updated",
                    "message": f"Dispute {saved['dispute_id']} was {saved['status'].lower()}.",
                },
            )
        return saved
