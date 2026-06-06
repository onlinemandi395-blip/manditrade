from __future__ import annotations

from datetime import UTC, datetime

from services.id_service import IdService
from services.performance_service import PerformanceService


class OrderService:
    def __init__(self, data_service, notification_service) -> None:
        self.data_service = data_service
        self.notification_service = notification_service
        self.id_service = IdService()
        self.performance_service = PerformanceService()

    def create_marketplace_order(self, *, items: list[dict], buyer_email: str) -> dict:
        with self.performance_service.measure("order_create_marketplace"):
            first_item = dict((items or [{}])[0])
            owner = dict(first_item.get("owner", {}) or {})
            record = {
                "order_id": self.id_service.next("order"),
                "items": items,
                "source_channel": "marketplace",
                "product_id": first_item.get("product_id", ""),
                "buyer_email": buyer_email,
                "owner_email": owner.get("email", ""),
                "owner_role": owner.get("role", ""),
                "role": "public_buyer",
                "status": "PLACED",
                "created_at": datetime.now(UTC).isoformat(),
            }
            self.data_service._bootstrap_collection("orders").append(record)
            self.notification_service.create_notification(
                notification_type="ORDER_CREATED",
                title="Order created",
                message="A new marketplace order entered the queue.",
                metadata={
                    "order_id": record["order_id"],
                    "source_channel": "marketplace",
                    "to_email": owner.get("email", ""),
                    "product_id": record["product_id"],
                },
            )
            self.notification_service.create_notification(
                notification_type="ORDER_CREATED",
                title="Marketplace order routed",
                message="Marketplace order routed through product manufacturer.",
                metadata={"order_id": record["order_id"]},
            )
            return record

    def create_manditrade_order(self, *, product: dict, requesting_user_email: str) -> dict:
        with self.performance_service.measure("order_create_manditrade"):
            owner = dict(product.get("owner", {}) or {})
            record = {
                "order_id": self.id_service.next("order"),
                "source_channel": "manditrade",
                "product_id": product.get("product_id", ""),
                "requesting_user_email": requesting_user_email,
                "owner_email": owner.get("email", ""),
                "owner_role": owner.get("role", ""),
                "admin_routed": True,
                "status": "REQUESTED",
                "created_at": datetime.now(UTC).isoformat(),
            }
            self.data_service._bootstrap_collection("orders").append(record)
            if owner.get("email"):
                self.notification_service.create_notification(
                    notification_type="ORDER_CREATED",
                    title="MandiTrade order routed",
                    message="A MandiTrade order was routed through product ownership.",
                    metadata={"order_id": record["order_id"], "source_channel": "manditrade", "to_email": owner.get("email", "")},
                )
            self.notification_service.create_notification(
                notification_type="ORDER_CREATED",
                title="MandiTrade order requested",
                message="A MandiTrade order was routed to platform admin.",
                metadata={"order_id": record["order_id"], "source_channel": "manditrade"},
            )
            return record
