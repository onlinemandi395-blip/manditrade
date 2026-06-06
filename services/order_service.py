from __future__ import annotations

from datetime import UTC, datetime

from services.id_service import IdService
from services.ledger_service import LedgerService
from services.performance_service import PerformanceService


class OrderService:
    def __init__(self, data_service, notification_service) -> None:
        self.data_service = data_service
        self.notification_service = notification_service
        self.id_service = IdService()
        self.ledger_service = LedgerService(data_service)
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
                "product_name": first_item.get("product_name", ""),
                "buyer_email": buyer_email,
                "owner_email": owner.get("email", ""),
                "owner_role": owner.get("role", ""),
                "quantity": sum(float(item.get("quantity", 1) or 1) for item in items) if items else 1,
                "unit_price": float((((first_item.get("sales_channels") or {}).get("marketplace") or {}).get("price", 0)) or 0),
                "total_amount": sum(float(item.get("total", item.get("price", 0)) or 0) for item in items) if items else float((((first_item.get("sales_channels") or {}).get("marketplace") or {}).get("price", 0)) or 0),
                "role": "public_buyer",
                "status": "PLACED",
                "created_at": datetime.now(UTC).isoformat(),
            }
            self.data_service._bootstrap_collection("orders").append(record)
            self.ledger_service.create_order_receivable(
                order_id=record["order_id"],
                source_channel="marketplace",
                owner_email=owner.get("email", ""),
                owner_role=owner.get("role", ""),
                amount=record["total_amount"],
                metadata={"buyer_email": buyer_email, "product_id": record["product_id"]},
            )
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
                "product_name": product.get("product_name", ""),
                "requester_email": requesting_user_email,
                "owner_email": owner.get("email", ""),
                "owner_role": owner.get("role", ""),
                "admin_routed": True,
                "quantity": 1,
                "unit_price": float((((product.get("sales_channels") or {}).get("manditrade") or {}).get("price", 0)) or 0),
                "total_amount": float((((product.get("sales_channels") or {}).get("manditrade") or {}).get("price", 0)) or 0),
                "status": "REQUESTED",
                "created_at": datetime.now(UTC).isoformat(),
            }
            self.data_service._bootstrap_collection("orders").append(record)
            self.ledger_service.create_order_receivable(
                order_id=record["order_id"],
                source_channel="manditrade",
                owner_email=owner.get("email", ""),
                owner_role=owner.get("role", ""),
                amount=record["total_amount"],
                metadata={"requester_email": requesting_user_email, "product_id": record["product_id"]},
            )
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
