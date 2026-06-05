from __future__ import annotations

from datetime import UTC, datetime

from services.id_service import IdService


class OrderService:
    def __init__(self, data_service, notification_service) -> None:
        self.data_service = data_service
        self.notification_service = notification_service
        self.id_service = IdService()

    def create_order(self, *, items: list[dict], source_channel: str, role: str) -> dict:
        record = {
            "order_id": self.id_service.next("order"),
            "items": items,
            "source_channel": source_channel,
            "role": role,
            "status": "CREATED",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.data_service._bootstrap_collection("orders").append(record)
        self.notification_service.create_notification(
            notification_type="ORDER_CREATED",
            title="Order created",
            message="A new order entered the queue.",
            metadata={"order_id": record["order_id"], "source_channel": source_channel},
        )
        return record
