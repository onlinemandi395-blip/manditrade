from __future__ import annotations

from datetime import UTC, datetime

from services.auth_service import get_bootstrap_primary_admin
from services.id_service import IdService


class LedgerService:
    def __init__(self, data_service) -> None:
        self.data_service = data_service
        self.id_service = IdService()

    def create_order_receivable(
        self,
        *,
        order_id: str,
        source_channel: str,
        owner_email: str,
        owner_role: str,
        amount: float,
        metadata: dict | None = None,
    ) -> dict:
        primary_admin = get_bootstrap_primary_admin()
        record = {
            "ledger_id": self.id_service.next("ledger"),
            "order_id": order_id,
            "source_channel": source_channel,
            "party_a": {
                "email": primary_admin.get("email", ""),
                "role": "platform_admin",
            },
            "party_b": {
                "email": owner_email,
                "role": owner_role,
            },
            "amount": float(amount or 0),
            "entry_type": "ORDER_RECEIVABLE",
            "status": "OPEN",
            "metadata": metadata or {},
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.data_service.get_collection_ref("ledger").append(record)
        return record
