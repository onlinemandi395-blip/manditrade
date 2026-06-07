from __future__ import annotations

from datetime import UTC, datetime
import random

from services.id_service import IdService
from services.ledger_service import LedgerService
from services.payment_service import PaymentService
from services.performance_service import PerformanceService


class OrderService:
    def __init__(self, data_service, notification_service) -> None:
        self.data_service = data_service
        self.notification_service = notification_service
        self.id_service = IdService()
        self.ledger_service = LedgerService(data_service)
        self.payment_service = PaymentService(data_service, data_service.cache_service)
        self.performance_service = PerformanceService()

    def _find_order(self, order_id: str) -> dict | None:
        return next(
            (row for row in self.data_service.get_collection_ref("orders") if str(row.get("order_id", "")).strip() == str(order_id).strip()),
            None,
        )

    def _find_payment(self, payment_id: str) -> dict | None:
        return next(
            (row for row in self.data_service.get_collection_ref("payments") if str(row.get("payment_id", "")).strip() == str(payment_id).strip()),
            None,
        )

    def _find_shipment(self, order_id: str) -> dict | None:
        return next(
            (row for row in self.data_service.get_collection_ref("shipments") if str(row.get("order_id", "")).strip() == str(order_id).strip()),
            None,
        )

    def create_marketplace_order(self, *, items: list[dict], buyer_email: str) -> dict:
        with self.performance_service.measure("order_create_marketplace"):
            first_item = dict((items or [{}])[0])
            owner = dict(first_item.get("owner", {}) or {})
            delivery_partner = dict(first_item.get("delivery_partner", {}) or {})
            pricing = dict(first_item.get("pricing", {}) or {})
            quantity = sum(float(item.get("quantity", 1) or 1) for item in items) if items else 1
            sell_price = float(pricing.get("marketplace_price", 0) or 0)
            admin_price = float(pricing.get("admin_price", 0) or 0)
            record = {
                "order_id": self.id_service.next("order"),
                "items": items,
                "source_channel": "marketplace",
                "market_type": "B2C",
                "product_id": first_item.get("product_id", ""),
                "product_name": first_item.get("product_name", ""),
                "buyer_email": buyer_email,
                "owner_email": owner.get("email", ""),
                "owner_role": owner.get("role", ""),
                "preferred_delivery_partner_email": delivery_partner.get("email", ""),
                "quantity": quantity,
                "unit_price": sell_price,
                "sell_price": sell_price,
                "admin_price": admin_price,
                "admin_margin": round(sell_price - admin_price, 2),
                "total_amount": round(sell_price * quantity, 2),
                "role": "public_buyer",
                "status": "PAYMENT_PENDING",
                "admin_status": "PAYMENT_PENDING",
                "owner_status": "AWAITING_PAYMENT_VERIFICATION",
                "delivery_status": "NOT_ASSIGNED",
                "otp_status": "NOT_GENERATED",
                "created_at": datetime.now(UTC).isoformat(),
            }
            self.data_service._bootstrap_collection("orders").append(record)
            payment_record = self.payment_service.create_payment_record(
                order_id=record["order_id"],
                payer_email=buyer_email,
                amount=record["total_amount"],
                payment_type="MARKETPLACE",
                created_by=buyer_email,
            )
            record["payment_id"] = payment_record["payment_id"]
            record["payment_reference"] = payment_record["payment_reference"]
            record["upi_link"] = payment_record["upi_link"]
            record["qr_payload"] = payment_record["qr_payload"]
            self.notification_service.create_notification(
                to_email=owner.get("email", ""),
                title="Order created",
                message="A new marketplace order is waiting for payment verification.",
                event_type="ORDER_CREATED",
                to_role=owner.get("role", ""),
                owner_email=owner.get("email", ""),
                source_entity="orders",
                source_id=record["order_id"],
                metadata={"product_id": record["product_id"], "source_channel": "marketplace"},
                created_by=buyer_email,
            )
            self.notification_service.create_notification(
                to_email=buyer_email,
                title="Marketplace order created",
                message="Your marketplace order was created. Complete payment using the generated UPI reference.",
                event_type="ORDER_CREATED",
                source_entity="orders",
                source_id=record["order_id"],
                metadata={"product_id": record["product_id"], "source_channel": "marketplace"},
                created_by=buyer_email,
            )
            self.notification_service.create_notification(
                to_email="",
                title="Marketplace payment pending",
                message="A marketplace order is awaiting payment verification.",
                event_type="ORDER_CREATED",
                to_role="platform_admin",
                owner_email=owner.get("email", ""),
                source_entity="orders",
                source_id=record["order_id"],
                metadata={"product_id": record["product_id"], "source_channel": "marketplace"},
                created_by=buyer_email,
            )
            return record

    def create_manditrade_order(self, *, product: dict, requesting_user_email: str) -> dict:
        with self.performance_service.measure("order_create_manditrade"):
            owner = dict(product.get("owner", {}) or {})
            delivery_partner = dict(product.get("delivery_partner", {}) or {})
            pricing = dict(product.get("pricing", {}) or {})
            sell_price = float(pricing.get("manditrade_price", 0) or 0)
            admin_price = float(pricing.get("admin_price", 0) or 0)
            record = {
                "order_id": self.id_service.next("order"),
                "source_channel": "manditrade",
                "market_type": "B2B",
                "product_id": product.get("product_id", ""),
                "product_name": product.get("product_name", ""),
                "requester_email": requesting_user_email,
                "owner_email": owner.get("email", ""),
                "owner_role": owner.get("role", ""),
                "preferred_delivery_partner_email": delivery_partner.get("email", ""),
                "admin_routed": True,
                "quantity": 1,
                "unit_price": sell_price,
                "sell_price": sell_price,
                "admin_price": admin_price,
                "admin_margin": round(sell_price - admin_price, 2),
                "total_amount": sell_price,
                "status": "PAYMENT_PENDING",
                "admin_status": "PAYMENT_PENDING",
                "owner_status": "AWAITING_PAYMENT_VERIFICATION",
                "delivery_status": "NOT_ASSIGNED",
                "otp_status": "NOT_GENERATED",
                "created_at": datetime.now(UTC).isoformat(),
            }
            self.data_service._bootstrap_collection("orders").append(record)
            payment_record = self.payment_service.create_payment_record(
                order_id=record["order_id"],
                payer_email=requesting_user_email,
                amount=record["total_amount"],
                payment_type="MANDITRADE",
                created_by=requesting_user_email,
            )
            record["payment_id"] = payment_record["payment_id"]
            record["payment_reference"] = payment_record["payment_reference"]
            record["upi_link"] = payment_record["upi_link"]
            record["qr_payload"] = payment_record["qr_payload"]
            if owner.get("email"):
                self.notification_service.create_notification(
                    to_email=owner.get("email", ""),
                    title="MandiTrade order routed",
                    message="A MandiTrade order is waiting for payment verification.",
                    event_type="ORDER_CREATED",
                    to_role=owner.get("role", ""),
                    owner_email=owner.get("email", ""),
                    source_entity="orders",
                    source_id=record["order_id"],
                    metadata={"source_channel": "manditrade"},
                    created_by=requesting_user_email,
                )
            self.notification_service.create_notification(
                to_email=requesting_user_email,
                title="MandiTrade order requested",
                message="Your MandiTrade request was created. Complete payment using the generated UPI reference.",
                event_type="ORDER_CREATED",
                source_entity="orders",
                source_id=record["order_id"],
                metadata={"source_channel": "manditrade"},
                created_by=requesting_user_email,
            )
            self.notification_service.create_notification(
                to_email="",
                title="MandiTrade payment pending",
                message="A MandiTrade order is awaiting payment verification.",
                event_type="ORDER_CREATED",
                to_role="platform_admin",
                owner_email=owner.get("email", ""),
                source_entity="orders",
                source_id=record["order_id"],
                metadata={"source_channel": "manditrade"},
                created_by=requesting_user_email,
            )
            return record

    def verify_payment(
        self,
        *,
        order_id: str,
        amount_received: float,
        transaction_reference: str,
        notes: str,
        verified_by: str,
    ) -> dict:
        order = self._find_order(order_id)
        if not order:
            raise ValueError("Order not found.")
        payment = self._find_payment(order.get("payment_id", ""))
        if not payment:
            raise ValueError("Payment record not found.")
        now = datetime.now(UTC).isoformat()
        payment["amount_received"] = round(float(amount_received or 0), 2)
        payment["transaction_reference"] = transaction_reference.strip()
        payment["notes"] = notes.strip()
        payment["status"] = "PAYMENT_VERIFIED"
        payment["verified_by"] = verified_by
        payment["verified_at"] = now
        order["status"] = "PAYMENT_VERIFIED"
        order["admin_status"] = "PAYMENT_VERIFIED"
        order["owner_status"] = "ACTION_REQUIRED"
        order["updated_at"] = now
        order["updated_by"] = verified_by
        owner_email = str(order.get("owner_email", "")).strip().lower()
        owner_role = str(order.get("owner_role", "")).strip().lower()
        buyer_email = str(order.get("buyer_email", "") or order.get("requester_email", "")).strip().lower()
        self.notification_service.create_notification(
            to_email=owner_email,
            title="Payment verified",
            message=f"Payment verified for order {order_id}. Please review the order.",
            event_type="PAYMENT_VERIFIED",
            to_role=owner_role,
            owner_email=owner_email,
            source_entity="payments",
            source_id=payment.get("payment_id", ""),
            created_by=verified_by,
        )
        if buyer_email:
            self.notification_service.create_notification(
                to_email=buyer_email,
                title="Payment verified",
                message=f"Your payment was verified for order {order_id}.",
                event_type="PAYMENT_VERIFIED",
                source_entity="payments",
                source_id=payment.get("payment_id", ""),
                created_by=verified_by,
            )
        return {"order": order, "payment": payment}

    def owner_accept_order(self, *, order_id: str, owner_email: str) -> dict:
        order = self._find_order(order_id)
        if not order:
            raise ValueError("Order not found.")
        if str(order.get("owner_email", "")).strip().lower() != str(owner_email).strip().lower():
            raise ValueError("Order is not assigned to this owner.")
        now = datetime.now(UTC).isoformat()
        order["status"] = "OWNER_ACCEPTED"
        order["owner_status"] = "ACCEPTED"
        order["updated_at"] = now
        order["updated_by"] = owner_email
        buyer_email = str(order.get("buyer_email", "") or order.get("requester_email", "")).strip().lower()
        self.notification_service.create_notification(
            to_email="",
            title="Owner accepted order",
            message=f"Owner accepted order {order_id}.",
            event_type="OWNER_ACCEPTED",
            to_role="platform_admin",
            owner_email=owner_email,
            source_entity="orders",
            source_id=order_id,
            created_by=owner_email,
        )
        if buyer_email:
            self.notification_service.create_notification(
                to_email=buyer_email,
                title="Order accepted",
                message=f"Your order {order_id} was accepted by the owner.",
                event_type="OWNER_ACCEPTED",
                source_entity="orders",
                source_id=order_id,
                created_by=owner_email,
            )
        return order

    def owner_reject_order(self, *, order_id: str, owner_email: str, reason: str = "") -> dict:
        order = self._find_order(order_id)
        if not order:
            raise ValueError("Order not found.")
        if str(order.get("owner_email", "")).strip().lower() != str(owner_email).strip().lower():
            raise ValueError("Order is not assigned to this owner.")
        now = datetime.now(UTC).isoformat()
        order["status"] = "OWNER_REJECTED"
        order["owner_status"] = "REJECTED"
        order["owner_rejection_reason"] = reason.strip()
        order["updated_at"] = now
        order["updated_by"] = owner_email
        buyer_email = str(order.get("buyer_email", "") or order.get("requester_email", "")).strip().lower()
        self.notification_service.create_notification(
            to_email="",
            title="Owner rejected order",
            message=f"Owner rejected order {order_id}.",
            event_type="OWNER_REJECTED",
            to_role="platform_admin",
            owner_email=owner_email,
            source_entity="orders",
            source_id=order_id,
            created_by=owner_email,
        )
        if buyer_email:
            self.notification_service.create_notification(
                to_email=buyer_email,
                title="Order rejected",
                message=f"Your order {order_id} was rejected by the owner.",
                event_type="OWNER_REJECTED",
                source_entity="orders",
                source_id=order_id,
                created_by=owner_email,
            )
        return order

    def owner_mark_ready_for_pickup(self, *, order_id: str, owner_email: str) -> dict:
        order = self._find_order(order_id)
        if not order:
            raise ValueError("Order not found.")
        if str(order.get("owner_email", "")).strip().lower() != str(owner_email).strip().lower():
            raise ValueError("Order is not assigned to this owner.")
        now = datetime.now(UTC).isoformat()
        order["status"] = "READY_FOR_PICKUP"
        order["owner_status"] = "READY_FOR_PICKUP"
        order["updated_at"] = now
        order["updated_by"] = owner_email
        buyer_email = str(order.get("buyer_email", "") or order.get("requester_email", "")).strip().lower()
        self.notification_service.create_notification(
            to_email="",
            title="Ready for pickup",
            message=f"Order {order_id} is ready for pickup.",
            event_type="READY_FOR_PICKUP",
            to_role="platform_admin",
            owner_email=owner_email,
            source_entity="orders",
            source_id=order_id,
            created_by=owner_email,
        )
        if buyer_email:
            self.notification_service.create_notification(
                to_email=buyer_email,
                title="Order ready for pickup",
                message=f"Your order {order_id} is ready for pickup.",
                event_type="READY_FOR_PICKUP",
                source_entity="orders",
                source_id=order_id,
                created_by=owner_email,
            )
        return order

    def assign_delivery_partner(self, *, order_id: str, delivery_partner_email: str, assigned_by: str) -> dict:
        order = self._find_order(order_id)
        if not order:
            raise ValueError("Order not found.")
        now = datetime.now(UTC).isoformat()
        shipment = self._find_shipment(order_id)
        if not shipment:
            shipment = {
                "shipment_id": self.id_service.next("shipment"),
                "order_id": order_id,
                "product_id": order.get("product_id", ""),
                "buyer_email": str(order.get("buyer_email", "") or order.get("requester_email", "")).strip().lower(),
                "owner_email": str(order.get("owner_email", "")).strip().lower(),
                "owner_role": str(order.get("owner_role", "")).strip().lower(),
                "created_at": now,
            }
            self.data_service.get_collection_ref("shipments").append(shipment)
        shipment["delivery_partner_email"] = str(delivery_partner_email).strip().lower()
        shipment["status"] = "PICKUP_ASSIGNED"
        shipment["assigned_at"] = now
        shipment["assigned_by"] = assigned_by
        order["status"] = "PICKUP_ASSIGNED"
        order["admin_status"] = "PICKUP_ASSIGNED"
        order["delivery_status"] = "PICKUP_ASSIGNED"
        order["updated_at"] = now
        order["updated_by"] = assigned_by
        self.notification_service.create_notification(
            to_email=shipment["delivery_partner_email"],
            title="Pickup assigned",
            message=f"Pickup assigned for order {order_id}.",
            event_type="PICKUP_ASSIGNED",
            to_role="delivery_partner",
            source_entity="shipments",
            source_id=shipment.get("shipment_id", ""),
            created_by=assigned_by,
        )
        self.notification_service.create_notification(
            to_email=shipment["owner_email"],
            title="Pickup assigned",
            message=f"Delivery partner assigned for order {order_id}.",
            event_type="PICKUP_ASSIGNED",
            to_role=shipment["owner_role"],
            owner_email=shipment["owner_email"],
            source_entity="shipments",
            source_id=shipment.get("shipment_id", ""),
            created_by=assigned_by,
        )
        return shipment

    def confirm_pickup(self, *, order_id: str, delivery_partner_email: str) -> dict:
        order = self._find_order(order_id)
        shipment = self._find_shipment(order_id)
        if not order or not shipment:
            raise ValueError("Shipment not found.")
        if str(shipment.get("delivery_partner_email", "")).strip().lower() != str(delivery_partner_email).strip().lower():
            raise ValueError("Shipment is not assigned to this delivery partner.")
        now = datetime.now(UTC).isoformat()
        shipment["status"] = "PICKED_UP"
        shipment["picked_up_at"] = now
        shipment["picked_up_by"] = delivery_partner_email
        otp_code = f"{random.randint(0, 999999):06d}"
        order["status"] = "PICKED_UP"
        order["delivery_status"] = "PICKED_UP"
        order["otp_status"] = "GENERATED"
        order["delivery_otp"] = otp_code
        order["updated_at"] = now
        order["updated_by"] = delivery_partner_email
        if not order.get("ledger_created_at"):
            self.ledger_service.create_order_receivable(
                order_id=order["order_id"],
                source_channel=order.get("source_channel", ""),
                owner_email=order.get("owner_email", ""),
                owner_role=order.get("owner_role", ""),
                amount=round(float(order.get("admin_price", 0) or 0) * float(order.get("quantity", 1) or 1), 2),
                product_id=order.get("product_id", ""),
                metadata={"trigger": "PICKED_UP", "buyer_email": str(order.get("buyer_email", "") or order.get("requester_email", "")).strip().lower()},
            )
            order["ledger_created_at"] = now
        buyer_email = str(order.get("buyer_email", "") or order.get("requester_email", "")).strip().lower()
        owner_email = str(order.get("owner_email", "")).strip().lower()
        owner_role = str(order.get("owner_role", "")).strip().lower()
        if buyer_email:
            self.notification_service.create_notification(
                to_email=buyer_email,
                title="Pickup completed",
                message=f"Pickup completed for order {order_id}. Delivery OTP: {otp_code}",
                event_type="PICKUP_COMPLETED",
                source_entity="shipments",
                source_id=shipment.get("shipment_id", ""),
                created_by=delivery_partner_email,
            )
        self.notification_service.create_notification(
            to_email="",
            title="Pickup completed",
            message=f"Pickup completed for order {order_id}. Ledger created.",
            event_type="PICKUP_COMPLETED",
            to_role="platform_admin",
            owner_email=owner_email,
            source_entity="shipments",
            source_id=shipment.get("shipment_id", ""),
            created_by=delivery_partner_email,
        )
        self.notification_service.create_notification(
            to_email=owner_email,
            title="Pickup completed",
            message=f"Pickup completed for order {order_id}.",
            event_type="PICKUP_COMPLETED",
            to_role=owner_role,
            owner_email=owner_email,
            source_entity="shipments",
            source_id=shipment.get("shipment_id", ""),
            created_by=delivery_partner_email,
        )
        return {"order": order, "shipment": shipment}

    def mark_in_transit(self, *, order_id: str, delivery_partner_email: str) -> dict:
        order = self._find_order(order_id)
        shipment = self._find_shipment(order_id)
        if not order or not shipment:
            raise ValueError("Shipment not found.")
        if str(shipment.get("delivery_partner_email", "")).strip().lower() != str(delivery_partner_email).strip().lower():
            raise ValueError("Shipment is not assigned to this delivery partner.")
        now = datetime.now(UTC).isoformat()
        shipment["status"] = "IN_TRANSIT"
        shipment["in_transit_at"] = now
        order["status"] = "IN_TRANSIT"
        order["delivery_status"] = "IN_TRANSIT"
        order["updated_at"] = now
        order["updated_by"] = delivery_partner_email
        return {"order": order, "shipment": shipment}

    def verify_delivery_otp(self, *, order_id: str, delivery_partner_email: str, otp_code: str) -> dict:
        order = self._find_order(order_id)
        shipment = self._find_shipment(order_id)
        if not order or not shipment:
            raise ValueError("Shipment not found.")
        if str(shipment.get("delivery_partner_email", "")).strip().lower() != str(delivery_partner_email).strip().lower():
            raise ValueError("Shipment is not assigned to this delivery partner.")
        expected_otp = str(order.get("delivery_otp", "")).strip()
        provided_otp = str(otp_code or "").strip()
        if not expected_otp or provided_otp != expected_otp:
            order["otp_status"] = "OTP_FAILED"
            order["updated_at"] = datetime.now(UTC).isoformat()
            order["updated_by"] = delivery_partner_email
            raise ValueError("Invalid delivery OTP.")
        now = datetime.now(UTC).isoformat()
        shipment["status"] = "DELIVERED"
        shipment["delivered_at"] = now
        shipment["delivered_by"] = delivery_partner_email
        order["status"] = "COMPLETED"
        order["delivery_status"] = "DELIVERED"
        order["otp_status"] = "VERIFIED"
        order["completed_at"] = now
        order["updated_at"] = now
        order["updated_by"] = delivery_partner_email
        buyer_email = str(order.get("buyer_email", "") or order.get("requester_email", "")).strip().lower()
        owner_email = str(order.get("owner_email", "")).strip().lower()
        owner_role = str(order.get("owner_role", "")).strip().lower()
        self.notification_service.create_notification(
            to_email="",
            title="Order delivered",
            message=f"Order {order_id} was delivered successfully.",
            event_type="DELIVERED",
            to_role="platform_admin",
            owner_email=owner_email,
            source_entity="shipments",
            source_id=shipment.get("shipment_id", ""),
            created_by=delivery_partner_email,
        )
        self.notification_service.create_notification(
            to_email=owner_email,
            title="Order delivered",
            message=f"Order {order_id} was delivered successfully.",
            event_type="DELIVERED",
            to_role=owner_role,
            owner_email=owner_email,
            source_entity="shipments",
            source_id=shipment.get("shipment_id", ""),
            created_by=delivery_partner_email,
        )
        if buyer_email:
            self.notification_service.create_notification(
                to_email=buyer_email,
                title="Order delivered",
                message=f"Your order {order_id} was delivered successfully.",
                event_type="DELIVERED",
                source_entity="shipments",
                source_id=shipment.get("shipment_id", ""),
                created_by=delivery_partner_email,
            )
        return {"order": order, "shipment": shipment}
