from __future__ import annotations

from datetime import UTC, datetime
import random

from services.id_service import IdService
from services.ledger_service import LedgerService
from services.payment_service import PaymentService
from services.performance_service import PerformanceService
from services.pricing_service import PricingService
from services.user_profile_service import UserProfileService


class OrderService:
    def __init__(self, data_service, notification_service) -> None:
        self.data_service = data_service
        self.notification_service = notification_service
        self.id_service = IdService()
        self.ledger_service = LedgerService(data_service)
        self.payment_service = PaymentService(data_service, data_service.cache_service)
        self.performance_service = PerformanceService()
        self.pricing_service = PricingService()
        self.user_profile_service = UserProfileService(data_service)

    def get_channel_quantity_rules(self, product: dict, channel: str) -> dict:
        normalized_channel = str(channel or "").strip().lower()
        if normalized_channel == "marketplace":
            return {"minimum_quantity": 1.0, "increment_quantity": 1.0}
        sales_channels = dict(product.get("sales_channels", {}) or {})
        channel_config = dict(sales_channels.get(normalized_channel, {}) or {})
        minimum_quantity = float(channel_config.get("minimum_quantity", 1) or 1)
        increment_quantity = float(channel_config.get("increment_quantity", 1) or 1)
        if minimum_quantity <= 0:
            minimum_quantity = 1.0
        if increment_quantity <= 0:
            increment_quantity = 1.0
        return {
            "minimum_quantity": minimum_quantity,
            "increment_quantity": increment_quantity,
        }

    def validate_channel_quantity(self, product: dict, channel: str, quantity: float) -> float:
        rules = self.get_channel_quantity_rules(product, channel)
        normalized_quantity = float(quantity or 0)
        minimum_quantity = float(rules["minimum_quantity"])
        increment_quantity = float(rules["increment_quantity"])
        if normalized_quantity < minimum_quantity:
            raise ValueError(
                f"Minimum quantity for {channel} is {minimum_quantity:g}."
            )
        if str(channel or "").strip().lower() == "marketplace":
            return max(1.0, round(normalized_quantity))
        remainder = (normalized_quantity - minimum_quantity) / increment_quantity
        if abs(remainder - round(remainder)) > 1e-9:
            raise ValueError(
                f"Quantity must start at {minimum_quantity:g} and increase by {increment_quantity:g}."
            )
        return normalized_quantity

    def _find_order(self, order_id: str) -> dict | None:
        normalized_order_id = str(order_id).strip()
        return next(
            (
                row
                for row in self.list_all_orders()
                if str(row.get("order_id", "")).strip() == normalized_order_id
            ),
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

    def _resolve_service_config(self, product: dict) -> dict:
        service_config = dict(product.get("service_config", {}) or {})
        return {
            "packaging_mode": str(service_config.get("packaging_mode", "owner") or "owner").strip().lower(),
            "shipping_mode": str(service_config.get("shipping_mode", "owner") or "owner").strip().lower(),
            "delivery_scope": str(service_config.get("delivery_scope", "custom") or "custom").strip().lower(),
            "packaging_cost_b2c": round(float(service_config.get("packaging_cost_b2c", 0) or 0), 2),
            "packaging_cost_b2b": round(float(service_config.get("packaging_cost_b2b", 0) or 0), 2),
            "shipping_cost_b2c": round(float(service_config.get("shipping_cost_b2c", 0) or 0), 2),
            "shipping_cost_b2b": round(float(service_config.get("shipping_cost_b2b", 0) or 0), 2),
            "delivery_notes": str(service_config.get("delivery_notes", "") or "").strip(),
        }

    def _resolve_commission_percent(self, *, pricing: dict, channel: str, sell_price: float, merchant_price: float) -> float:
        normalized_channel = str(channel or "").strip().lower()
        field_name = "marketplace_commission_percent" if normalized_channel == "marketplace" else "manditrade_commission_percent"
        commission_percent = float(pricing.get(field_name, 0) or 0)
        if commission_percent > 0:
            return round(min(100.0, max(0.0, commission_percent)), 2)
        if float(sell_price or 0) <= 0:
            return 0.0
        derived_percent = ((float(sell_price or 0) - float(merchant_price or 0)) / float(sell_price or 1)) * 100
        return round(min(100.0, max(0.0, derived_percent)), 2)

    def _build_commission_totals(self, *, merchandise_total: float, sell_price: float, merchant_price: float, quantity: float, commission_percent: float) -> dict:
        normalized_commission_percent = round(min(100.0, max(0.0, float(commission_percent or 0))), 2)
        if normalized_commission_percent > 0:
            platform_margin = round(float(merchandise_total or 0) * normalized_commission_percent / 100, 2)
            owner_payable_amount = round(float(merchandise_total or 0) - platform_margin, 2)
            merchant_unit_price = round(owner_payable_amount / float(quantity or 1), 2) if float(quantity or 0) > 0 else round(float(merchant_price or 0), 2)
        else:
            owner_payable_amount = round(float(merchant_price or 0) * float(quantity or 0), 2)
            platform_margin = round(float(merchandise_total or 0) - owner_payable_amount, 2)
            merchant_unit_price = round(float(merchant_price or 0), 2)
        return {
            "platform_commission_percent": normalized_commission_percent,
            "platform_margin": round(platform_margin, 2),
            "owner_payable_amount": round(owner_payable_amount, 2),
            "merchant_unit_price": merchant_unit_price,
        }

    def _build_financial_breakdown(self, *, product: dict, channel: str, quantity: float, sell_price: float) -> dict:
        normalized_channel = "b2c" if str(channel or "").strip().lower() == "marketplace" else "b2b"
        pricing = dict(product.get("pricing", {}) or {})
        service_config = self._resolve_service_config(product)
        merchandise_total = round(float(sell_price or 0) * float(quantity or 0), 2)
        merchant_price = round(float(pricing.get("admin_price", 0) or 0), 2)
        commission_percent = self._resolve_commission_percent(
            pricing=pricing,
            channel=channel,
            sell_price=sell_price,
            merchant_price=merchant_price,
        )
        commission_totals = self._build_commission_totals(
            merchandise_total=merchandise_total,
            sell_price=sell_price,
            merchant_price=merchant_price,
            quantity=quantity,
            commission_percent=commission_percent,
        )
        owner_payable_amount = round(float(commission_totals.get("owner_payable_amount", 0) or 0), 2)
        packaging_charge = round(
            float(service_config.get("packaging_cost_b2c" if normalized_channel == "b2c" else "packaging_cost_b2b", 0) or 0)
            * float(quantity or 0),
            2,
        )
        shipping_charge = round(
            float(service_config.get("shipping_cost_b2c" if normalized_channel == "b2c" else "shipping_cost_b2b", 0) or 0)
            * float(quantity or 0),
            2,
        )
        platform_margin = round(float(commission_totals.get("platform_margin", 0) or 0), 2)
        total_amount = round(merchandise_total + packaging_charge + shipping_charge, 2)
        return {
            "merchandise_total": merchandise_total,
            "owner_payable_amount": owner_payable_amount,
            "platform_margin": platform_margin,
            "platform_commission_percent": round(float(commission_totals.get("platform_commission_percent", commission_percent) or commission_percent), 2),
            "merchant_unit_price": round(float(commission_totals.get("merchant_unit_price", merchant_price) or merchant_price), 2),
            "packaging_charge": packaging_charge,
            "shipping_charge": shipping_charge,
            "total_amount": total_amount,
            "packaging_mode": service_config.get("packaging_mode", "owner"),
            "shipping_mode": service_config.get("shipping_mode", "owner"),
            "delivery_scope": service_config.get("delivery_scope", "custom"),
            "delivery_notes": service_config.get("delivery_notes", ""),
        }

    def list_marketplace_orders(self) -> list[dict]:
        rows = self.data_service.get_collection_ref("marketplace_orders")
        for row in rows:
            row["source_channel"] = "marketplace"
        return rows

    def list_manditrade_orders(self) -> list[dict]:
        rows = self.data_service.get_collection_ref("manditrade_orders")
        for row in rows:
            row["source_channel"] = "manditrade"
        return rows

    def list_all_orders(self) -> list[dict]:
        return self.list_marketplace_orders() + self.list_manditrade_orders()

    def estimate_cart_totals(self, *, items: list[dict], product_lookup: dict[str, dict]) -> dict:
        merchandise_total = 0.0
        packaging_total = 0.0
        shipping_total = 0.0
        grand_total = 0.0
        normalized_items: list[dict] = []
        for item in items or []:
            product_id = str(item.get("product_id", "")).strip()
            product = dict(product_lookup.get(product_id, {}) or {})
            if not product:
                continue
            channel = str(item.get("channel", "marketplace") or "marketplace").strip().lower() or "marketplace"
            quantity = float(item.get("quantity", item.get("qty", 1)) or 1)
            sell_price = self.pricing_service.resolve_sell_price(product, channel)
            breakdown = self._build_financial_breakdown(
                product=product,
                channel=channel,
                quantity=quantity,
                sell_price=sell_price,
            )
            merchandise_total += float(breakdown.get("merchandise_total", 0) or 0)
            packaging_total += float(breakdown.get("packaging_charge", 0) or 0)
            shipping_total += float(breakdown.get("shipping_charge", 0) or 0)
            grand_total += float(breakdown.get("total_amount", 0) or 0)
            normalized_items.append(
                {
                    "product_id": product_id,
                    "channel": channel,
                    "quantity": quantity,
                    "unit_price": sell_price,
                    "line_total": round(float(sell_price or 0) * float(quantity or 0), 2),
                }
            )
        return {
            "items": normalized_items,
            "merchandise_total": round(merchandise_total, 2),
            "packaging_charge": round(packaging_total, 2),
            "shipping_charge": round(shipping_total, 2),
            "grand_total": round(grand_total, 2),
        }

    def _get_order_collection_name(self, source_channel: str) -> str:
        normalized = str(source_channel or "").strip().lower()
        if normalized == "marketplace":
            return "marketplace_orders"
        if normalized in {"manditrade", "mandiplace"}:
            return "manditrade_orders"
        raise ValueError(f"Unsupported order source_channel: {source_channel}")

    def persist_order_storage(self, order_or_id) -> None:
        order = order_or_id if isinstance(order_or_id, dict) else self._find_order(str(order_or_id))
        if not order:
            raise ValueError("Order not found.")
        self.data_service.persist_collection(self._get_order_collection_name(order.get("source_channel", "")))
        self.user_profile_service.sync_order_record(order=order)

    def delete_order_for_admin(self, *, order_id: str, deleted_by: str) -> dict:
        normalized_order_id = str(order_id or "").strip()
        if not normalized_order_id:
            raise ValueError("Order ID is required.")
        order = self._find_order(normalized_order_id)
        if not order:
            raise ValueError("Order not found.")
        collection_name = self._get_order_collection_name(order.get("source_channel", ""))
        orders = self.data_service.get_collection_ref(collection_name)
        order = next((row for row in orders if str(row.get("order_id", "")).strip() == normalized_order_id), order)

        payment_id = str(order.get("payment_id", "")).strip()
        shipments = self.data_service.get_collection_ref("shipments")
        ledger = self.data_service.get_collection_ref("ledger")
        notifications = self.data_service.get_collection_ref("notifications")
        gmail_queue = self.data_service.get_collection_ref("gmail_queue")

        shipment_ids = [
            str(row.get("shipment_id", "")).strip()
            for row in shipments
            if str(row.get("order_id", "")).strip() == normalized_order_id
        ]
        related_notification_ids = {
            str(row.get("notification_id", "")).strip()
            for row in notifications
            if (
                str(row.get("source_entity", "")).strip() in {"orders", "payments", "shipments"}
                and str(row.get("source_id", "")).strip() in {normalized_order_id, payment_id, *shipment_ids}
            )
        }

        orders[:] = [row for row in orders if str(row.get("order_id", "")).strip() != normalized_order_id]
        if payment_id:
            payments = self.data_service.get_collection_ref("payments")
            payments[:] = [
                row
                for row in payments
                if str(row.get("payment_id", "")).strip() != payment_id
                and str(row.get("order_id", "")).strip() != normalized_order_id
            ]
        shipments[:] = [row for row in shipments if str(row.get("order_id", "")).strip() != normalized_order_id]
        ledger[:] = [row for row in ledger if str(row.get("order_id", "")).strip() != normalized_order_id]
        notifications[:] = [
            row
            for row in notifications
            if str(row.get("notification_id", "")).strip() not in related_notification_ids
        ]
        gmail_queue[:] = [
            row
            for row in gmail_queue
            if str(row.get("notification_id", "")).strip() not in related_notification_ids
        ]
        self.notification_service.create_notification(
            to_email="",
            title="Order deleted",
            message=f"Order {normalized_order_id} was deleted by admin.",
            event_type="ORDER_DELETED",
            to_role="platform_admin",
            source_entity="orders",
            source_id=normalized_order_id,
            created_by=deleted_by,
        )
        return {
            "order_id": normalized_order_id,
            "payment_id": payment_id,
            "shipment_ids": shipment_ids,
            "collection_name": collection_name,
            "deleted_notification_count": len(related_notification_ids),
        }

    def create_marketplace_order(self, *, items: list[dict], buyer_email: str) -> dict:
        product_lookup = {}
        for item in items or []:
            product_id = str(item.get("product_id", "")).strip()
            if product_id:
                product_lookup[product_id] = dict(item)
        return self.create_marketplace_order_with_checkout(
            items=items,
            buyer_email=buyer_email,
            buyer_name="",
            buyer_mobile="",
            delivery_address={},
            product_lookup=product_lookup,
        )

    def create_marketplace_order_with_checkout(
        self,
        *,
        items: list[dict],
        buyer_email: str,
        buyer_name: str,
        buyer_mobile: str,
        delivery_address: dict,
        product_lookup: dict[str, dict],
    ) -> dict:
        with self.performance_service.measure("order_create_marketplace"):
            if not items:
                raise ValueError("Cart is empty.")
            normalized_items = []
            total_amount = 0.0
            owner = {}
            owner_business_details = {}
            delivery_partner = {}
            admin_price = 0.0
            owner_payable_amount = 0.0
            platform_margin_total = 0.0
            commission_totals = 0.0
            packaging_total = 0.0
            shipping_total = 0.0
            service_config = {}
            for item in items:
                product_id = str(item.get("product_id", "")).strip()
                product = dict(product_lookup.get(product_id, {}) or {})
                if not product:
                    raise ValueError(f"Product not found for cart item: {product_id}")
                quantity = self.validate_channel_quantity(
                    product,
                    "marketplace",
                    float(item.get("quantity", item.get("qty", 1)) or 1),
                )
                unit_price = self.pricing_service.resolve_sell_price(product, "marketplace")
                line_total = round(unit_price * quantity, 2)
                pricing = dict(product.get("pricing", {}) or {})
                breakdown = self._build_financial_breakdown(product=product, channel="marketplace", quantity=quantity, sell_price=unit_price)
                normalized_items.append(
                    {
                        "product_id": product_id,
                        "product_name": product.get("product_name", ""),
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "line_total": line_total,
                        "platform_commission_percent": breakdown.get("platform_commission_percent", 0),
                        "merchant_unit_price": breakdown.get("merchant_unit_price", float(pricing.get("admin_price", 0) or 0)),
                    }
                )
                total_amount += line_total
                owner_payable_amount += float(breakdown.get("owner_payable_amount", 0) or 0)
                platform_margin_total += float(breakdown.get("platform_margin", 0) or 0)
                commission_totals += float(breakdown.get("platform_commission_percent", 0) or 0) * line_total
                packaging_total += float(breakdown.get("packaging_charge", 0) or 0)
                shipping_total += float(breakdown.get("shipping_charge", 0) or 0)
                if not owner:
                    owner = dict(product.get("owner", {}) or {})
                    owner_business_details = dict(product.get("owner_business_details", {}) or {})
                    delivery_partner = dict(product.get("delivery_partner", {}) or {})
                    admin_price = float(pricing.get("admin_price", 0) or 0)
                    service_config = self._resolve_service_config(product)

            first_item = normalized_items[0]
            grand_total = round(total_amount + packaging_total + shipping_total, 2)
            record = {
                "order_id": self.id_service.next_drive_id(self.data_service.admin_drive_service, "marketplace_order", "MKTORD"),
                "items": normalized_items,
                "source_channel": "marketplace",
                "market_type": "B2C",
                "product_id": first_item.get("product_id", ""),
                "product_name": first_item.get("product_name", ""),
                "buyer_email": buyer_email,
                "buyer": {
                    "email": str(buyer_email or "").strip().lower(),
                    "name": str(buyer_name or "").strip(),
                    "mobile": str(buyer_mobile or "").strip(),
                },
                "delivery_address": {
                    "address_line_1": str(delivery_address.get("address_line_1", "")).strip(),
                    "address_line_2": str(delivery_address.get("address_line_2", "")).strip(),
                    "city": str(delivery_address.get("city", "")).strip(),
                    "district": str(delivery_address.get("district", "")).strip(),
                    "state": str(delivery_address.get("state", "")).strip(),
                    "pin_code": str(delivery_address.get("pin_code", "")).strip(),
                    "landmark": str(delivery_address.get("landmark", "")).strip(),
                },
                "owner_email": owner.get("email", ""),
                "owner_role": owner.get("role", ""),
                "preferred_delivery_partner_email": delivery_partner.get("email", ""),
                "quantity": sum(float(item.get("quantity", 1) or 1) for item in normalized_items),
                "unit_price": float(first_item.get("unit_price", 0) or 0),
                "sell_price": float(first_item.get("unit_price", 0) or 0),
                "admin_price": admin_price,
                "admin_margin": round(platform_margin_total, 2),
                "merchandise_total": round(total_amount, 2),
                "total_amount": grand_total,
                "internal": {
                    "owner_email": owner.get("email", ""),
                    "owner_role": owner.get("role", ""),
                    "admin_price": admin_price,
                    "owner_payable_amount": round(owner_payable_amount, 2),
                    "admin_margin": round(platform_margin_total, 2),
                    "platform_commission_percent_effective": round((commission_totals / total_amount), 2) if total_amount > 0 else 0.0,
                },
                "financials": {
                    "merchandise_total": round(total_amount, 2),
                    "packaging_charge": round(packaging_total, 2),
                    "shipping_charge": round(shipping_total, 2),
                    "platform_margin": round(platform_margin_total, 2),
                    "owner_payable_amount": round(owner_payable_amount, 2),
                    "grand_total": grand_total,
                    "platform_commission_percent_effective": round((commission_totals / total_amount), 2) if total_amount > 0 else 0.0,
                },
                "service_config": service_config,
                "role": "public_buyer",
                "status": "PAYMENT_PENDING",
                "payment_status": "PENDING",
                "admin_status": "PAYMENT_PENDING",
                "owner_status": "WAITING_PAYMENT",
                "delivery_status": "NOT_ASSIGNED",
                "otp_status": "NOT_GENERATED",
                "created_at": datetime.now(UTC).isoformat(),
                "owner_profile_completed": False,
                "posting_status": "DUE_FOR_POSTING",
            }
            receiver_config = self.payment_service.get_receiver_config_for_owner(
                owner_email=owner.get("email", ""),
                owner_role=owner.get("role", ""),
                owner_business_details=owner_business_details,
            )
            record["owner_profile_completed"] = bool(receiver_config.get("profile_completed", False))
            record["posting_status"] = "READY_TO_POST" if record["owner_profile_completed"] else "DUE_FOR_POSTING"
            self.data_service.get_collection_ref("marketplace_orders").append(record)
            payment_record = self.payment_service.create_payment_record(
                order_id=record["order_id"],
                payer_email=buyer_email,
                amount=record["total_amount"],
                payment_type="MARKETPLACE",
                created_by=buyer_email,
                owner_email=owner.get("email", ""),
                owner_role=owner.get("role", ""),
                owner_business_details=owner_business_details,
            )
            record["payment_id"] = payment_record["payment_id"]
            record["payment_reference"] = payment_record["payment_reference"]
            record["upi_link"] = payment_record["upi_link"]
            record["qr_payload"] = payment_record["qr_payload"]
            self.notification_service.create_notification(
                to_email=owner.get("email", ""),
                title="Order created",
                message="A new marketplace order is waiting for your payment confirmation.",
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
            return record

    def create_manditrade_order(self, *, product: dict, requesting_user_email: str) -> dict:
        return self.create_manditrade_order_with_checkout(
            product=product,
            requesting_user_email=requesting_user_email,
            requester_name="",
            requester_mobile="",
            delivery_address={},
        )

    def create_manditrade_order_with_checkout(
        self,
        *,
        product: dict,
        requesting_user_email: str,
        requester_name: str,
        requester_mobile: str,
        delivery_address: dict,
        requested_quantity: float = 1.0,
    ) -> dict:
        with self.performance_service.measure("order_create_manditrade"):
            owner = dict(product.get("owner", {}) or {})
            delivery_partner = dict(product.get("delivery_partner", {}) or {})
            pricing = dict(product.get("pricing", {}) or {})
            sell_price = self.pricing_service.resolve_sell_price(product, "manditrade")
            quantity = self.validate_channel_quantity(product, "manditrade", requested_quantity)
            admin_price = float(pricing.get("admin_price", 0) or 0)
            service_config = self._resolve_service_config(product)
            breakdown = self._build_financial_breakdown(product=product, channel="manditrade", quantity=quantity, sell_price=sell_price)
            record = {
                "order_id": self.id_service.next_drive_id(self.data_service.admin_drive_service, "manditrade_order", "MDTORD"),
                "source_channel": "manditrade",
                "market_type": "B2B",
                "product_id": product.get("product_id", ""),
                "product_name": product.get("product_name", ""),
                "requester_email": requesting_user_email,
                "requester": {
                    "email": str(requesting_user_email or "").strip().lower(),
                    "name": str(requester_name or "").strip(),
                    "mobile": str(requester_mobile or "").strip(),
                },
                "delivery_address": {
                    "address_line_1": str(delivery_address.get("address_line_1", "")).strip(),
                    "address_line_2": str(delivery_address.get("address_line_2", "")).strip(),
                    "city": str(delivery_address.get("city", "")).strip(),
                    "district": str(delivery_address.get("district", "")).strip(),
                    "state": str(delivery_address.get("state", "")).strip(),
                    "pin_code": str(delivery_address.get("pin_code", "")).strip(),
                    "landmark": str(delivery_address.get("landmark", "")).strip(),
                },
                "owner_email": owner.get("email", ""),
                "owner_role": owner.get("role", ""),
                "preferred_delivery_partner_email": delivery_partner.get("email", ""),
                "admin_routed": True,
                "items": [
                    {
                        "product_id": product.get("product_id", ""),
                        "product_name": product.get("product_name", ""),
                        "quantity": quantity,
                        "unit_price": sell_price,
                        "line_total": round(sell_price * quantity, 2),
                        "platform_commission_percent": breakdown.get("platform_commission_percent", 0),
                        "merchant_unit_price": breakdown.get("merchant_unit_price", admin_price),
                    }
                ],
                "quantity": quantity,
                "unit_price": sell_price,
                "sell_price": sell_price,
                "admin_price": admin_price,
                "admin_margin": round(float(breakdown.get("platform_margin", 0) or 0), 2),
                "merchandise_total": round(sell_price * quantity, 2),
                "total_amount": round(breakdown.get("total_amount", sell_price * quantity), 2),
                "internal": {
                    "owner_email": owner.get("email", ""),
                    "owner_role": owner.get("role", ""),
                    "admin_price": admin_price,
                    "owner_payable_amount": breakdown.get("owner_payable_amount", round(admin_price * quantity, 2)),
                    "admin_margin": round(float(breakdown.get("platform_margin", 0) or 0), 2),
                    "platform_commission_percent_effective": round(float(breakdown.get("platform_commission_percent", 0) or 0), 2),
                },
                "financials": {
                    "merchandise_total": breakdown.get("merchandise_total", round(sell_price * quantity, 2)),
                    "packaging_charge": breakdown.get("packaging_charge", 0.0),
                    "shipping_charge": breakdown.get("shipping_charge", 0.0),
                    "platform_margin": breakdown.get("platform_margin", round((sell_price - admin_price) * quantity, 2)),
                    "owner_payable_amount": breakdown.get("owner_payable_amount", round(admin_price * quantity, 2)),
                    "grand_total": breakdown.get("total_amount", round(sell_price * quantity, 2)),
                    "platform_commission_percent_effective": round(float(breakdown.get("platform_commission_percent", 0) or 0), 2),
                },
                "service_config": service_config,
                "status": "PAYMENT_PENDING",
                "payment_status": "PENDING",
                "admin_status": "PAYMENT_PENDING",
                "owner_status": "WAITING_PAYMENT",
                "delivery_status": "NOT_ASSIGNED",
                "otp_status": "NOT_GENERATED",
                "created_at": datetime.now(UTC).isoformat(),
                "owner_profile_completed": False,
                "posting_status": "DUE_FOR_POSTING",
            }
            receiver_config = self.payment_service.get_receiver_config_for_owner(
                owner_email=owner.get("email", ""),
                owner_role=owner.get("role", ""),
                owner_business_details=dict(product.get("owner_business_details", {}) or {}),
            )
            record["owner_profile_completed"] = bool(receiver_config.get("profile_completed", False))
            record["posting_status"] = "READY_TO_POST" if record["owner_profile_completed"] else "DUE_FOR_POSTING"
            self.data_service.get_collection_ref("manditrade_orders").append(record)
            payment_record = self.payment_service.create_payment_record(
                order_id=record["order_id"],
                payer_email=requesting_user_email,
                amount=record["total_amount"],
                payment_type="MANDITRADE",
                created_by=requesting_user_email,
                owner_email=owner.get("email", ""),
                owner_role=owner.get("role", ""),
                owner_business_details=dict(product.get("owner_business_details", {}) or {}),
            )
            record["payment_id"] = payment_record["payment_id"]
            record["payment_reference"] = payment_record["payment_reference"]
            record["upi_link"] = payment_record["upi_link"]
            record["qr_payload"] = payment_record["qr_payload"]
            if owner.get("email"):
                self.notification_service.create_notification(
                    to_email=owner.get("email", ""),
                    title="MandiTrade order routed",
                    message="A MandiTrade order is waiting for your payment confirmation.",
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
            return record

    def owner_verify_payment(
        self,
        *,
        order_id: str,
        amount_received: float,
        transaction_reference: str,
        notes: str,
        owner_email: str,
    ) -> dict:
        order = self._find_order(order_id)
        if not order:
            raise ValueError("Order not found.")
        if str(order.get("owner_email", "")).strip().lower() != str(owner_email or "").strip().lower():
            raise ValueError("Only the assigned owner can verify this payment.")
        payment = self._find_payment(order.get("payment_id", ""))
        if not payment:
            raise ValueError("Payment record not found.")
        now = datetime.now(UTC).isoformat()
        payment["amount_received"] = round(float(amount_received or 0), 2)
        payment["transaction_reference"] = transaction_reference.strip()
        payment["notes"] = notes.strip()
        payment["status"] = "PAYMENT_VERIFIED"
        payment["payment_status"] = "VERIFIED"
        payment["verified_by"] = owner_email
        payment["verified_at"] = now
        financials = dict(order.get("financials", {}) or {})
        internal = dict(order.get("internal", {}) or {})
        if "quoted_financials" not in order:
            order["quoted_financials"] = dict(financials)
        if "quoted_internal" not in order:
            order["quoted_internal"] = dict(internal)
        packaging_charge = round(float(financials.get("packaging_charge", 0) or 0), 2)
        shipping_charge = round(float(financials.get("shipping_charge", 0) or 0), 2)
        quoted_merchandise_total = round(float(financials.get("merchandise_total", order.get("merchandise_total", 0)) or 0), 2)
        effective_commission_percent = round(float(internal.get("platform_commission_percent_effective", financials.get("platform_commission_percent_effective", 0)) or 0), 2)
        realized_grand_total = round(float(amount_received or 0), 2)
        realized_merchandise_total = max(0.0, round(realized_grand_total - packaging_charge - shipping_charge, 2))
        if realized_merchandise_total <= 0 and quoted_merchandise_total > 0:
            realized_merchandise_total = quoted_merchandise_total
        realized_platform_margin = round(realized_merchandise_total * effective_commission_percent / 100, 2)
        realized_owner_payable = round(realized_merchandise_total - realized_platform_margin, 2)
        financials["merchandise_total"] = realized_merchandise_total
        financials["platform_margin"] = realized_platform_margin
        financials["owner_payable_amount"] = realized_owner_payable
        financials["grand_total"] = realized_grand_total
        financials["platform_commission_percent_effective"] = effective_commission_percent
        financials["commission_confirmed_at"] = now
        internal["owner_payable_amount"] = realized_owner_payable
        internal["admin_margin"] = realized_platform_margin
        internal["platform_commission_percent_effective"] = effective_commission_percent
        order["financials"] = financials
        order["internal"] = internal
        order["admin_margin"] = realized_platform_margin
        order["merchandise_total"] = realized_merchandise_total
        order["total_amount"] = realized_grand_total
        payment["platform_commission_percent_effective"] = effective_commission_percent
        payment["platform_commission_amount"] = realized_platform_margin
        payment["owner_payable_amount"] = realized_owner_payable
        if not order.get("ledger_created_at"):
            self.ledger_service.create_order_runtime_entries(
                order=order,
                trigger="PAYMENT_VERIFIED",
                created_by=owner_email,
            )
            order["ledger_created_at"] = now
        order["status"] = "OWNER_ACCEPTED"
        order["payment_status"] = "VERIFIED"
        order["admin_status"] = "OWNER_CONFIRMED"
        order["owner_status"] = "ACCEPTED"
        order["updated_at"] = now
        order["updated_by"] = owner_email
        owner_email = str(order.get("owner_email", "")).strip().lower()
        owner_role = str(order.get("owner_role", "")).strip().lower()
        buyer_email = str(order.get("buyer_email", "") or order.get("requester_email", "")).strip().lower()
        self.notification_service.create_notification(
            to_email=owner_email,
            title="Payment confirmed",
            message=f"You confirmed payment for order {order_id}. Schedule it for pickup when ready.",
            event_type="PAYMENT_VERIFIED",
            to_role=owner_role,
            owner_email=owner_email,
            source_entity="payments",
            source_id=payment.get("payment_id", ""),
            created_by=owner_email,
        )
        if buyer_email:
            self.notification_service.create_notification(
                to_email=buyer_email,
                title="Order confirmed",
                message=f"Your payment was confirmed and order {order_id} is accepted.",
                event_type="PAYMENT_VERIFIED",
                source_entity="payments",
                source_id=payment.get("payment_id", ""),
                created_by=owner_email,
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
        financials = dict(order.get("financials", {}) or {})
        service_config = dict(order.get("service_config", {}) or {})
        shipment = self._find_shipment(order_id)
        if not shipment:
            shipment = {
                "shipment_id": self.id_service.next("shipment"),
                "order_id": order_id,
                "product_id": order.get("product_id", ""),
                "buyer_email": str(order.get("buyer_email", "") or order.get("requester_email", "")).strip().lower(),
                "owner_email": str(order.get("owner_email", "")).strip().lower(),
                "owner_role": str(order.get("owner_role", "")).strip().lower(),
                "source_channel": str(order.get("source_channel", "")).strip().lower(),
                "market_type": str(order.get("market_type", "")).strip().upper(),
                "created_at": now,
            }
            self.data_service.get_collection_ref("shipments").append(shipment)
        shipment["delivery_partner_email"] = str(delivery_partner_email).strip().lower()
        shipment["status"] = "PICKUP_ASSIGNED"
        shipment["assigned_at"] = now
        shipment["assigned_by"] = assigned_by
        shipment["shipping_mode"] = str(service_config.get("shipping_mode", "owner") or "owner").strip().lower()
        shipment["delivery_scope"] = str(service_config.get("delivery_scope", "custom") or "custom").strip().lower()
        shipment["delivery_notes"] = str(service_config.get("delivery_notes", "") or "").strip()
        shipment["shipping_charge"] = round(float(financials.get("shipping_charge", 0) or 0), 2)
        shipment["packaging_charge"] = round(float(financials.get("packaging_charge", 0) or 0), 2)
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
            to_role="worker",
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
            raise ValueError("Shipment is not assigned to this worker.")
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
            self.ledger_service.create_order_runtime_entries(
                order=order,
                trigger="PICKED_UP",
                created_by=delivery_partner_email,
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
            raise ValueError("Shipment is not assigned to this worker.")
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
            raise ValueError("Shipment is not assigned to this worker.")
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
