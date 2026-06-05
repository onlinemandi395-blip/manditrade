from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class PublicOrderService:
    def __init__(
        self,
        *,
        public_orders_root: Path,
        public_payments_root: Path,
        public_buyer_service,
        public_cart_service,
        product_catalog_service,
        dual_inventory_service,
        notification_center_service,
        gmail_service,
        governance_service,
        safe_drive_write_service,
        json_service,
        id_allocator_service,
        pricing_service=None,
        config: dict[str, Any] | None = None,
        trust_badge_service=None,
        event_notification_service=None,
        settlement_service=None,
        invoice_service=None,
    ) -> None:
        self.public_orders_root = public_orders_root
        self.public_payments_root = public_payments_root
        self.public_buyer_service = public_buyer_service
        self.public_cart_service = public_cart_service
        self.product_catalog_service = product_catalog_service
        self.dual_inventory_service = dual_inventory_service
        self.notification_center_service = notification_center_service
        self.gmail_service = gmail_service
        self.governance_service = governance_service
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.id_allocator_service = id_allocator_service
        self.pricing_service = pricing_service
        self.config = config or {}
        self.trust_badge_service = trust_badge_service
        self.event_notification_service = event_notification_service
        self.settlement_service = settlement_service
        self.invoice_service = invoice_service

    def _upsert_marketplace_shipment(self, order: dict[str, Any], *, status: str, actor_email: str) -> None:
        if not self.governance_service:
            return
        seller_id = str(order.get("assigned_seller_manufacturer_id", "")).strip().upper()
        if not seller_id:
            return
        warehouse = self.governance_service.ensure_default_warehouse(
            owner_role="manufacturer",
            owner_id=seller_id,
            warehouse_name=f"{seller_id} Main Warehouse",
        )
        logistics = dict(order.get("logistics") or {})
        shipment_id = str(order.get("shipment_id") or "").strip().upper() or self.id_allocator_service.allocate("shipment")
        shipment = self.governance_service.upsert_shipment(
            {
                "shipment_id": shipment_id,
                "order_id": order.get("public_order_id", ""),
                "shipment_type": "MARKETPLACE",
                "source_warehouse_id": warehouse.get("warehouse_id", ""),
                "destination_city": str((order.get("buyer_profile") or {}).get("city", "")),
                "destination_state": str((order.get("buyer_profile") or {}).get("state", "")),
                "packaging_id": "",
                "courier_id": "",
                "tracking_number": str(logistics.get("vehicle_number", "") or logistics.get("transport_mode", "")),
                "weight": float(len(order.get("items", [])) or 0),
                "package_count": max(len(order.get("items", [])), 1),
                "courier_cost": 0.0,
                "status": status,
                "related_public_buyer_id": order.get("public_buyer_id", ""),
                "manufacturer_code": seller_id,
                "updated_by": actor_email,
            }
        )
        path = self._order_path(order["public_order_id"], order["created_at"])

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload["shipment_id"] = shipment["shipment_id"]
            payload["updated_at"] = datetime.now(UTC).isoformat()
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator)

    def list_orders_for_buyer(self, public_buyer_id: str) -> list[dict[str, Any]]:
        return [item for item in self.list_all_orders() if item.get("public_buyer_id") == public_buyer_id]

    def list_orders_for_seller(self, manufacturer_code: str) -> list[dict[str, Any]]:
        return [item for item in self.list_all_orders() if item.get("assigned_seller_manufacturer_id") == manufacturer_code]

    def list_all_orders(self) -> list[dict[str, Any]]:
        if not self.public_orders_root.exists():
            return []
        rows = []
        for path in sorted(self.public_orders_root.glob("*/*.json")):
            rows.append(self.json_service.read_json(path, {}))
        rows.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return rows

    def create_order_from_cart(self, public_buyer_id: str) -> dict[str, Any]:
        buyer = self.public_buyer_service.get_by_id(public_buyer_id)
        if buyer is None:
            raise ValueError(f"Public buyer not found: {public_buyer_id}")
        cart = self.public_cart_service.get_cart(public_buyer_id)
        items = list(cart.get("items", []))
        if not items:
            raise ValueError("Public cart is empty.")
        seller_id = cart.get("assigned_seller_manufacturer_id", "")
        if not seller_id:
            raise ValueError("Public cart is missing a seller assignment.")
        product_index = {item.get("product_id", ""): item for item in self.product_catalog_service.list_products(include_pending=False, viewer_role="public_buyer")}
        enriched_items = []
        for item in items:
            product = product_index.get(item.get("product_id", ""), {})
            enriched_items.append(
                {
                    **item,
                    "source_type": product.get("source_type", ""),
                    "source_name": product.get("source_name", ""),
                    "source_contact_person": product.get("source_contact_person", ""),
                    "source_mobile": product.get("source_mobile", ""),
                    "source_email": product.get("source_email", ""),
                    "source_city": product.get("source_city", ""),
                    "source_state": product.get("source_state", ""),
                    "source_confirmed": bool(product.get("source_confirmed", False)),
                    "procurement_price": float(product.get("procurement_price", 0) or 0),
                    "lead_time_days": int(product.get("lead_time_days", 0) or 0),
                }
            )
        items = enriched_items
        primary_source = next(
            (
                {
                    "source_type": item.get("source_type", ""),
                    "source_name": item.get("source_name", ""),
                    "source_contact_person": item.get("source_contact_person", ""),
                    "source_mobile": item.get("source_mobile", ""),
                    "source_email": item.get("source_email", ""),
                    "source_city": item.get("source_city", ""),
                    "source_state": item.get("source_state", ""),
                    "source_confirmed": bool(item.get("source_confirmed", False)),
                }
                for item in items
                if str(item.get("source_name") or item.get("source_email") or item.get("source_mobile") or "").strip()
            ),
            {},
        )
        order = {
            "schema_version": "1.0",
            "public_order_id": self.id_allocator_service.allocate("public_order"),
            "public_buyer_id": public_buyer_id,
            "buyer_email": buyer.get("email", ""),
            "buyer_profile": {
                "city": buyer.get("city", ""),
                "state": buyer.get("state", ""),
            },
            "items": items,
            "total_amount": float(cart.get("payment_required", 0)),
            "payment_mode": self._payment_config().get("mode", "UPI_MANUAL"),
            "payment_status": "PENDING",
            "payment_reference": "",
            "payment_screenshot_placeholder": "",
            "payment_proof_url": "",
            "payment_proof_uploaded_at": "",
            "payment_verified_by": "",
            "payment_verified_at": "",
            "payment_receiver": seller_id,
            "status": "PAYMENT_PENDING",
            "assigned_seller_manufacturer_id": seller_id,
            "product_source_snapshot": primary_source,
            "inventory_reserved": False,
            "commission_breakdown": [
                self.pricing_service.calculate_commission(
                    {
                        "mandi_price": float(item.get("mandi_price", 0) or 0),
                        "marketplace_price": float(item.get("marketplace_price", item.get("mrp", 0)) or 0),
                    },
                    self.pricing_service.CHANNEL_PUBLIC_MARKETPLACE,
                    (self.governance_service.get_manufacturer(seller_id) or {}).get("subscription_plan", "basic"),
                )
                for item in items
            ] if self.pricing_service else [],
            "commission_status": "CALCULATED",
            "logistics": {
                "logistics_owner": "platform_admin",
                "delivery_status": "",
                "transport_mode": "",
                "driver_name": "",
                "driver_mobile": "",
                "vehicle_number": "",
                "dispatch_time": "",
                "expected_delivery": "",
                "dispatch_note": "",
                "delivery_note": "",
                "proof_url": "",
                "proof_image_url": "",
                "delivered_at": "",
            },
            "status_history": [
                {"status": "PAYMENT_PENDING", "at": datetime.now(UTC).isoformat(), "actor": buyer.get("email", "")}
            ],
            "ratings": [],
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        reserve_items = [{"product_id": item["product_id"], "qty": int(item["qty"])} for item in items]
        self.dual_inventory_service.reserve_self_inventory(
            seller_id,
            reserve_items,
            related_order_id=order["public_order_id"],
            note="Marketplace checkout reserved stock",
            created_by=buyer.get("email", ""),
        )
        order["inventory_reserved"] = True
        self.safe_drive_write_service.replace_document(self._order_path(order["public_order_id"], order["created_at"]), order)
        if self.settlement_service:
            self.settlement_service.ensure_transaction(
                transaction_type="MARKETPLACE",
                related_order_id=order["public_order_id"],
                payer_role="public_buyer",
                payer_id=public_buyer_id,
                payee_role="manufacturer",
                payee_id=seller_id,
                gross_amount=float(order.get("total_amount", 0) or 0),
                commission_amount=sum(float(item.get("admin_net_commission", item.get("admin_commission", 0)) or 0) for item in order.get("commission_breakdown", []) or []),
                net_amount=float(order.get("total_amount", 0) or 0),
                payment_mode=order.get("payment_mode", "UPI_MANUAL"),
                status="PENDING",
                created_by=buyer.get("email", "system"),
                metadata={"public_order_id": order["public_order_id"]},
            )
        self._record_payment_event(order["public_order_id"], "ORDER_CREATED", {"status": "PAYMENT_PENDING", "amount": order["total_amount"]})
        self.notification_center_service.create_public_notification(
            public_buyer_id,
            user_id=buyer.get("email", ""),
            notification_type="PUBLIC_ORDER_CREATED",
            priority="PENDING",
            title="Public order created",
            message="Your marketplace order was created. Complete full upfront payment to proceed.",
            source_type="PUBLIC_ORDER",
            source_id=order["public_order_id"],
            source_route="Marketplace Orders",
            thumbnail_url=str((items[0] if items else {}).get("thumbnail_url", "")),
            severity="MEDIUM",
        )
        self.gmail_service.enqueue_message(
            buyer.get("email", ""),
            f"Payment instructions for {order['public_order_id']}",
            self.build_payment_instruction_text(order),
            "public_order_created",
        )
        self._emit_event(
            "MARKETPLACE_ORDER_CREATED",
            entity_type="PUBLIC_ORDER",
            entity_id=order["public_order_id"],
            title="Marketplace order created",
            message=f"Marketplace order {order['public_order_id']} was created.",
            public_buyer_id=public_buyer_id,
            public_buyer_email=buyer.get("email", ""),
            manufacturer_code=seller_id,
            manufacturer_email=((self.governance_service.get_manufacturer(seller_id) or {}).get("owner_email", "")),
            thumbnail_url=str((items[0] if items else {}).get("thumbnail_url", "")),
        )
        self.public_cart_service.clear_cart(public_buyer_id)
        self._audit(
            action="PUBLIC_ORDER_CREATED",
            actor=buyer.get("email", ""),
            role="public_buyer",
            entity_id=order["public_order_id"],
            details={"status": order["status"], "payment_status": order["payment_status"]},
        )
        return order

    def submit_payment_reference(self, public_order_id: str, public_buyer_id: str, *, payment_reference: str, screenshot_placeholder: str = "") -> dict[str, Any]:
        order = self.get_order(public_order_id)
        if order.get("public_buyer_id") != public_buyer_id:
            raise PermissionError("You can update only your own public order.")
        if order.get("status") != "PAYMENT_PENDING":
            raise ValueError("Payment reference can be submitted only while payment is pending.")
        reference = payment_reference.strip()
        if not reference:
            raise ValueError("Payment reference / UTR is required.")
        path = self._order_path(order["public_order_id"], order["created_at"])

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload["payment_reference"] = reference
            payload["payment_screenshot_placeholder"] = screenshot_placeholder.strip()
            payload["payment_proof_url"] = screenshot_placeholder.strip()
            payload["payment_proof_uploaded_at"] = datetime.now(UTC).isoformat()
            payload["payment_status"] = "SUBMITTED"
            payload["updated_at"] = datetime.now(UTC).isoformat()
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator)
        updated = self.get_order(public_order_id)
        if self.settlement_service:
            transaction = next(
                (item for item in self.settlement_service.list_transactions() if item.get("related_order_id") == public_order_id and item.get("transaction_type") == "MARKETPLACE"),
                None,
            )
            if transaction:
                self.settlement_service.attach_payment_proof(
                    financial_transaction_id=transaction["financial_transaction_id"],
                    proof_url=updated.get("payment_proof_url", ""),
                    payment_reference=reference,
                    actor_id=updated.get("buyer_email", ""),
                )
        seller_id = updated.get("assigned_seller_manufacturer_id", "")
        if seller_id:
            self.notification_center_service.create_notification(
                seller_id,
                user_id=seller_id,
                notification_type="PUBLIC_PAYMENT_SUBMITTED",
                priority="HIGH",
                title="Public payment submitted",
                message=f"Buyer submitted payment reference for {public_order_id}.",
                source_type="PUBLIC_ORDER",
                source_id=public_order_id,
                source_route="Marketplace Orders",
                thumbnail_url=str((updated.get("items") or [{}])[0].get("thumbnail_url", "")),
                severity="HIGH",
            )
        self._emit_event(
            "PAYMENT_SUBMITTED",
            entity_type="PUBLIC_ORDER",
            entity_id=public_order_id,
            title="Payment submitted",
            message=f"Payment was submitted for {public_order_id}.",
            public_buyer_id=updated.get("public_buyer_id", ""),
            public_buyer_email=updated.get("buyer_email", ""),
            manufacturer_code=seller_id,
            manufacturer_email=((self.governance_service.get_manufacturer(seller_id) or {}).get("owner_email", "")),
            thumbnail_url=str((updated.get("items") or [{}])[0].get("thumbnail_url", "")),
        )
        self._record_payment_event(public_order_id, "PAYMENT_SUBMITTED", {"payment_reference": reference})
        self._audit(
            action="PUBLIC_PAYMENT_SUBMITTED",
            actor=updated.get("buyer_email", ""),
            role="public_buyer",
            entity_id=public_order_id,
            details={"payment_status": updated.get("payment_status", ""), "status": updated.get("status", "")},
        )
        return updated

    def verify_payment(self, public_order_id: str, verifier_user, *, approved: bool, note: str = "") -> dict[str, Any]:
        order = self.get_order(public_order_id)
        self._ensure_seller_access(order, verifier_user)
        if order.get("payment_status") != "SUBMITTED":
            raise ValueError("Payment can be verified only after buyer submits payment reference.")
        path = self._order_path(order["public_order_id"], order["created_at"])
        if not approved:
            def reject_mutator(payload: dict[str, Any]) -> dict[str, Any]:
                payload["payment_status"] = "FAILED"
                payload["status"] = "PAYMENT_PENDING"
                payload["seller_note"] = note.strip()
                payload["status_history"] = list(payload.get("status_history", [])) + [{"status": "PAYMENT_PENDING", "at": datetime.now(UTC).isoformat(), "actor": getattr(verifier_user, "email", "")}]
                payload["updated_at"] = datetime.now(UTC).isoformat()
                return payload
            self.safe_drive_write_service.mutate_json(path, reject_mutator)
            self._record_payment_event(public_order_id, "PAYMENT_REJECTED", {"note": note.strip()})
            updated = self.get_order(public_order_id)
            self._audit(
                action="PUBLIC_PAYMENT_REJECTED",
                actor=getattr(verifier_user, "email", ""),
                role=getattr(verifier_user, "role", ""),
                entity_id=public_order_id,
                details={"payment_status": updated.get("payment_status", ""), "status": updated.get("status", ""), "note": note.strip()},
            )
            return updated

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload["payment_status"] = "VERIFIED"
            payload["status"] = "PAID"
            payload["inventory_reserved"] = True
            payload["commission_status"] = "DUE"
            payload["seller_note"] = note.strip()
            payload["payment_verified_by"] = getattr(verifier_user, "email", "")
            payload["payment_verified_at"] = datetime.now(UTC).isoformat()
            payload["status_history"] = list(payload.get("status_history", [])) + [{"status": "PAID", "at": datetime.now(UTC).isoformat(), "actor": getattr(verifier_user, "email", "")}]
            payload["updated_at"] = datetime.now(UTC).isoformat()
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator)
        updated = self.get_order(public_order_id)
        if self.settlement_service:
            transaction = next(
                (item for item in self.settlement_service.list_transactions() if item.get("related_order_id") == public_order_id and item.get("transaction_type") == "MARKETPLACE"),
                None,
            )
            if transaction:
                self.settlement_service.record_payment(
                    financial_transaction_id=transaction["financial_transaction_id"],
                    amount=float(updated.get("total_amount", 0) or 0),
                    actor_id=getattr(verifier_user, "email", ""),
                    payment_reference=updated.get("payment_reference", ""),
                    payment_mode=updated.get("payment_mode", "UPI_MANUAL"),
                    payment_proof_url=updated.get("payment_proof_url", ""),
                    verified=True,
                    note=note,
                )
                if self.invoice_service:
                    seller = self.governance_service.get_manufacturer(updated.get("assigned_seller_manufacturer_id", "")) or {}
                    self.invoice_service.generate_invoice(
                        invoice_type="MARKETPLACE_INVOICE",
                        related_order_id=public_order_id,
                        bill_from={"manufacturer_code": updated.get("assigned_seller_manufacturer_id", ""), "name": seller.get("business_name", "")},
                        bill_to={"public_buyer_id": updated.get("public_buyer_id", ""), "email": updated.get("buyer_email", "")},
                        items=[
                            {
                                "name": item.get("name", item.get("product_name", "")),
                                "qty": item.get("qty", 0),
                                "unit": item.get("unit", ""),
                                "unit_price": item.get("marketplace_price", 0),
                            }
                            for item in updated.get("items", [])
                        ],
                        subtotal=float(updated.get("total_amount", 0) or 0),
                        commission_amount=sum(float(item.get("admin_net_commission", item.get("admin_commission", 0)) or 0) for item in updated.get("commission_breakdown", []) or []),
                    )
        self.notification_center_service.create_public_notification(
            updated["public_buyer_id"],
            user_id=updated.get("buyer_email", ""),
            notification_type="PUBLIC_PAYMENT_VERIFIED",
            priority="SUCCESS",
            title="Payment verified",
            message=f"Your payment for {public_order_id} was verified.",
            source_type="PUBLIC_ORDER",
            source_id=public_order_id,
            source_route="Marketplace Orders",
            thumbnail_url=str((updated.get("items") or [{}])[0].get("thumbnail_url", "")),
            severity="MEDIUM",
        )
        self.gmail_service.enqueue_message(
            updated.get("buyer_email", ""),
            f"Payment received for {public_order_id}",
            f"Payment for your public order {public_order_id} was verified successfully.",
            "public_payment_verified",
        )
        self._emit_event(
            "PAYMENT_VERIFIED",
            entity_type="PUBLIC_ORDER",
            entity_id=public_order_id,
            title="Payment verified",
            message=f"Payment was verified for {public_order_id}.",
            public_buyer_id=updated.get("public_buyer_id", ""),
            public_buyer_email=updated.get("buyer_email", ""),
            manufacturer_code=updated.get("assigned_seller_manufacturer_id", ""),
            manufacturer_email=((self.governance_service.get_manufacturer(updated.get("assigned_seller_manufacturer_id", "")) or {}).get("owner_email", "")),
            thumbnail_url=str((updated.get("items") or [{}])[0].get("thumbnail_url", "")),
        )
        self._record_payment_event(public_order_id, "PAYMENT_VERIFIED", {"note": note.strip()})
        self._audit(
            action="PUBLIC_PAYMENT_VERIFIED",
            actor=getattr(verifier_user, "email", ""),
            role=getattr(verifier_user, "role", ""),
            entity_id=public_order_id,
            details={"payment_status": updated.get("payment_status", ""), "status": updated.get("status", ""), "note": note.strip()},
        )
        return updated

    def confirm_order(self, public_order_id: str, seller_user) -> dict[str, Any]:
        order = self.get_order(public_order_id)
        self._ensure_seller_access(order, seller_user)
        if order.get("payment_status") != "VERIFIED":
            raise ValueError("Public order cannot be confirmed before payment verification.")
        return self._transition_order(
            public_order_id,
            allowed_statuses={"PAID"},
            next_status="CONFIRMED",
            buyer_notification=("PUBLIC_ORDER_CONFIRMED", "Public order confirmed", f"Your public order {public_order_id} is confirmed."),
            buyer_email_subject=f"Order confirmed: {public_order_id}",
            buyer_email_body=f"Your public marketplace order {public_order_id} is confirmed and will move to dispatch next.",
        )

    def dispatch_order(self, public_order_id: str, seller_user) -> dict[str, Any]:
        order = self.get_order(public_order_id)
        self._ensure_seller_access(order, seller_user)
        updated = self._transition_order(
            public_order_id,
            allowed_statuses={"CONFIRMED"},
            next_status="DISPATCHED",
            buyer_notification=("PUBLIC_ORDER_DISPATCHED", "Public order dispatched", f"Your public order {public_order_id} was dispatched."),
            buyer_email_subject=f"Dispatch update: {public_order_id}",
            buyer_email_body=f"Your public marketplace order {public_order_id} has been dispatched.",
        )
        self._upsert_marketplace_shipment(updated, status="IN_TRANSIT", actor_email=getattr(seller_user, "email", ""))
        return updated

    def confirm_delivery(self, public_order_id: str, acting_user) -> dict[str, Any]:
        order = self.get_order(public_order_id)
        if acting_user.role == "public_buyer":
            buyer = self.public_buyer_service.get_by_email(acting_user.email)
            if not buyer or buyer.get("public_buyer_id") != order.get("public_buyer_id"):
                raise PermissionError("You can confirm delivery only for your own public order.")
        else:
            self._ensure_seller_access(order, acting_user)
        self.dual_inventory_service.finalize_reserved(
            order["assigned_seller_manufacturer_id"],
            [{"product_id": item["product_id"], "qty": int(item["qty"])} for item in order.get("items", [])],
            bucket="self_inventory",
            related_order_id=public_order_id,
            note="Marketplace order delivered",
            created_by=getattr(acting_user, "email", ""),
        )
        updated = self._transition_order(
            public_order_id,
            allowed_statuses={"DISPATCHED"},
            next_status="DELIVERED",
            buyer_notification=("PUBLIC_ORDER_DELIVERED", "Public order delivered", f"Your public order {public_order_id} is marked delivered."),
            buyer_email_subject=f"Delivery complete: {public_order_id}",
            buyer_email_body=f"Your public marketplace order {public_order_id} has been marked delivered.",
        )
        self._upsert_marketplace_shipment(updated, status="DELIVERED", actor_email=getattr(acting_user, "email", ""))
        return updated

    def get_order(self, public_order_id: str) -> dict[str, Any]:
        for order in self.list_all_orders():
            if order.get("public_order_id") == public_order_id:
                return order
        raise ValueError(f"Public order not found: {public_order_id}")

    def update_logistics(
        self,
        public_order_id: str,
        *,
        actor,
        transport_mode: str = "",
        driver_name: str = "",
        driver_mobile: str = "",
        vehicle_number: str = "",
        dispatch_note: str = "",
        proof_url: str = "",
        delivery_status: str = "",
        expected_delivery: str = "",
    ) -> dict[str, Any]:
        order = self.get_order(public_order_id)
        self._ensure_seller_access(order, actor)
        path = self._order_path(order["public_order_id"], order["created_at"])

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload.setdefault("logistics", {})
            payload["logistics"].update(
                {
                    "logistics_owner": "platform_admin",
                    "transport_mode": transport_mode or payload["logistics"].get("transport_mode", ""),
                    "driver_name": driver_name or payload["logistics"].get("driver_name", ""),
                    "driver_mobile": driver_mobile or payload["logistics"].get("driver_mobile", ""),
                    "vehicle_number": vehicle_number or payload["logistics"].get("vehicle_number", ""),
                    "dispatch_time": datetime.now(UTC).isoformat() if delivery_status.upper() == "DISPATCHED" and not payload["logistics"].get("dispatch_time") else payload["logistics"].get("dispatch_time", ""),
                    "expected_delivery": expected_delivery or payload["logistics"].get("expected_delivery", ""),
                    "dispatch_note": dispatch_note or payload["logistics"].get("dispatch_note", ""),
                    "delivery_note": dispatch_note or payload["logistics"].get("delivery_note", ""),
                    "proof_url": proof_url or payload["logistics"].get("proof_url", ""),
                    "proof_image_url": proof_url or payload["logistics"].get("proof_image_url", ""),
                    "delivery_status": delivery_status or payload["logistics"].get("delivery_status", ""),
                }
            )
            payload["updated_at"] = datetime.now(UTC).isoformat()
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator)
        updated = self.get_order(public_order_id)
        self._audit(
            action="PUBLIC_LOGISTICS_UPDATED",
            actor=getattr(actor, "email", ""),
            role=getattr(actor, "role", ""),
            entity_id=public_order_id,
            details={"delivery_status": updated.get("logistics", {}).get("delivery_status", ""), "vehicle_number": updated.get("logistics", {}).get("vehicle_number", "")},
        )
        self._emit_event(
            "LOGISTICS_UPDATED",
            entity_type="PUBLIC_ORDER",
            entity_id=public_order_id,
            title="Logistics updated",
            message=f"Logistics updated for {public_order_id}.",
            public_buyer_id=updated.get("public_buyer_id", ""),
            public_buyer_email=updated.get("buyer_email", ""),
            manufacturer_code=updated.get("assigned_seller_manufacturer_id", ""),
            manufacturer_email=((self.governance_service.get_manufacturer(updated.get("assigned_seller_manufacturer_id", "")) or {}).get("owner_email", "")),
            thumbnail_url=str((updated.get("items") or [{}])[0].get("thumbnail_url", "")),
        )
        return updated

    def build_payment_instruction_text(self, order: dict[str, Any]) -> str:
        config = self._payment_config()
        seller = self.governance_service.get_manufacturer(order.get("assigned_seller_manufacturer_id", "")) or {}
        seller_upi = (((seller.get("banking") or {}).get("upi_id")) or "").strip()
        payee_name = (((seller.get("banking") or {}).get("account_holder_name")) or "").strip()
        upi_id = seller_upi or config.get("upi_id", "")
        payee = payee_name or config.get("payee_name", "")
        instructions = config.get("instructions", "Pay full amount upfront and enter UTR.")
        return (
            f"Order: {order['public_order_id']}\n"
            f"Amount: {order['total_amount']}\n"
            f"Mode: {order.get('payment_mode', 'UPI_MANUAL')}\n"
            f"Payee: {payee or 'Seller'}\n"
            f"UPI ID: {upi_id or 'To be shared by seller'}\n"
            f"Instructions: {instructions}"
        )

    def submit_feedback(self, public_order_id: str, *, rating: int, feedback: str, submitted_by: str) -> dict[str, Any]:
        order = self.get_order(public_order_id)
        path = self._order_path(order["public_order_id"], order["created_at"])
        feedback_row = {
            "rating": max(1, min(int(rating or 0), 5)),
            "feedback": feedback.strip(),
            "submitted_by": submitted_by,
            "created_at": datetime.now(UTC).isoformat(),
        }

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload.setdefault("ratings", [])
            payload["ratings"].append(feedback_row)
            payload["updated_at"] = datetime.now(UTC).isoformat()
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator)
        return self.get_order(public_order_id)

    def _payment_config(self) -> dict[str, Any]:
        return {
            "mode": "UPI_MANUAL",
            "upi_id": "",
            "payee_name": "",
            "instructions": "Pay full amount upfront and enter UTR.",
            **(self.config or {}),
        }

    def _transition_order(
        self,
        public_order_id: str,
        *,
        allowed_statuses: set[str],
        next_status: str,
        buyer_notification: tuple[str, str, str],
        buyer_email_subject: str,
        buyer_email_body: str,
    ) -> dict[str, Any]:
        order = self.get_order(public_order_id)
        if order.get("status") not in allowed_statuses:
            raise ValueError(f"Public order cannot move from {order.get('status')} to {next_status}.")
        path = self._order_path(order["public_order_id"], order["created_at"])

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload["status"] = next_status
            payload.setdefault("status_history", [])
            payload["status_history"].append({"status": next_status, "at": datetime.now(UTC).isoformat(), "actor": "system"})
            if next_status == "DISPATCHED":
                payload.setdefault("logistics", {})
                payload["logistics"]["logistics_owner"] = "platform_admin"
                payload["logistics"]["delivery_status"] = "DISPATCHED"
                payload["logistics"]["dispatch_time"] = datetime.now(UTC).isoformat()
            if next_status == "DELIVERED":
                payload.setdefault("logistics", {})
                payload["logistics"]["logistics_owner"] = "platform_admin"
                payload["logistics"]["delivery_status"] = "DELIVERED"
                payload["logistics"]["delivered_at"] = datetime.now(UTC).isoformat()
            payload["updated_at"] = datetime.now(UTC).isoformat()
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator)
        updated = self.get_order(public_order_id)
        notification_type, title, message = buyer_notification
        self.notification_center_service.create_public_notification(
            updated["public_buyer_id"],
            user_id=updated.get("buyer_email", ""),
            notification_type=notification_type,
            priority="OPEN",
            title=title,
            message=message,
            source_type="PUBLIC_ORDER",
            source_id=public_order_id,
            source_route="Marketplace Orders",
            thumbnail_url=str((updated.get("items") or [{}])[0].get("thumbnail_url", "")),
            severity="MEDIUM",
        )
        self.gmail_service.enqueue_message(updated.get("buyer_email", ""), buyer_email_subject, buyer_email_body, notification_type.lower())
        self._audit(
            action=f"PUBLIC_ORDER_{next_status}",
            actor="system",
            role="system",
            entity_id=public_order_id,
            details={"status": updated.get("status", ""), "delivery_status": updated.get("logistics", {}).get("delivery_status", "")},
        )
        self._emit_event(
            "ORDER_DISPATCHED" if next_status == "DISPATCHED" else "DELIVERY_COMPLETED" if next_status == "DELIVERED" else "STATUS_CHANGED",
            entity_type="PUBLIC_ORDER",
            entity_id=public_order_id,
            title=f"Order {next_status.replace('_', ' ').title()}",
            message=message,
            public_buyer_id=updated.get("public_buyer_id", ""),
            public_buyer_email=updated.get("buyer_email", ""),
            manufacturer_code=updated.get("assigned_seller_manufacturer_id", ""),
            manufacturer_email=((self.governance_service.get_manufacturer(updated.get("assigned_seller_manufacturer_id", "")) or {}).get("owner_email", "")),
            thumbnail_url=str((updated.get("items") or [{}])[0].get("thumbnail_url", "")),
        )
        return updated

    def _ensure_seller_access(self, order: dict[str, Any], acting_user) -> None:
        if acting_user.role == "platform_admin":
            return
        if acting_user.role not in {"manufacturer", "admin_as_manufacturer"}:
            raise PermissionError("Only seller manufacturer or platform admin can manage public orders.")
        if (acting_user.manufacturer_code or "").strip() != (order.get("assigned_seller_manufacturer_id") or "").strip():
            raise PermissionError("You can manage only public orders assigned to your manufacturer.")

    def _order_path(self, public_order_id: str, created_at: str) -> Path:
        month_key = datetime.fromisoformat(created_at).strftime("%Y-%m")
        target = self.public_orders_root / month_key / f"{public_order_id}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def _record_payment_event(self, public_order_id: str, event_type: str, payload: dict[str, Any]) -> None:
        month_key = datetime.now(UTC).strftime("%Y-%m")
        payment_id = self.id_allocator_service.allocate("public_payment")
        target = self.public_payments_root / month_key / f"{payment_id}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        self.safe_drive_write_service.replace_document(
            target,
            {
                "schema_version": "1.0",
                "payment_id": payment_id,
                "public_order_id": public_order_id,
                "event_type": event_type,
                "payload": payload,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )

    def _audit(self, *, action: str, actor: str, role: str, entity_id: str, details: dict[str, Any]) -> None:
        if not getattr(self.governance_service, "audit_service", None):
            return
        self.governance_service.audit_service.log_governance_event(
            actor=actor or "system",
            role=role or "system",
            action=action,
            entity_type="public_order",
            entity_id=entity_id,
            details=details,
        )

    def trust_badges_for_order(self, order: dict[str, Any]) -> list[str]:
        if not self.trust_badge_service:
            return []
        return self.trust_badge_service.badges_for_marketplace_order(order)

    def _emit_event(self, event_type: str, **payload: Any) -> None:
        if not self.event_notification_service:
            return
        self.event_notification_service.emit(event_type, payload)
