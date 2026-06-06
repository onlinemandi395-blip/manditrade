from __future__ import annotations

from datetime import UTC, datetime

from services.id_service import IdService


class OrderService:
    def __init__(self, data_service, notification_service) -> None:
        self.data_service = data_service
        self.notification_service = notification_service
        self.id_service = IdService()

    def create_marketplace_order(self, *, items: list[dict], buyer_email: str) -> dict:
        first_item = dict((items or [{}])[0])
        manufacturer = dict(first_item.get("manufacturer", {}) or {})
        record = {
            "order_id": self.id_service.next("order"),
            "items": items,
            "source_channel": "marketplace",
            "product_id": first_item.get("product_id", ""),
            "buyer_email": buyer_email,
            "manufacturer_email": manufacturer.get("email", ""),
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
                "to_email": manufacturer.get("email", ""),
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

    def create_manditrade_order(self, *, product: dict, requesting_manufacturer_email: str) -> dict:
        manufacturer = dict(product.get("manufacturer", {}) or {})
        mahajan = dict(product.get("mahajan", {}) or {})
        record = {
            "order_id": self.id_service.next("order"),
            "source_channel": "manditrade",
            "product_id": product.get("product_id", ""),
            "requesting_manufacturer_email": requesting_manufacturer_email,
            "assigned_manufacturer_email": manufacturer.get("email", ""),
            "mahajan_email": mahajan.get("email", ""),
            "admin_routed": True,
            "status": "REQUESTED",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.data_service._bootstrap_collection("orders").append(record)
        for email in [manufacturer.get("email", ""), mahajan.get("email", "")]:
            if email:
                self.notification_service.create_notification(
                    notification_type="ORDER_CREATED",
                    title="MandiTrade order routed",
                    message="A MandiTrade order was routed through product mapping.",
                    metadata={"order_id": record["order_id"], "source_channel": "manditrade", "to_email": email},
                )
        self.notification_service.create_notification(
            notification_type="ORDER_CREATED",
            title="MandiTrade order requested",
            message="A MandiTrade order was routed to platform admin.",
            metadata={"order_id": record["order_id"], "source_channel": "manditrade"},
        )
        return record
