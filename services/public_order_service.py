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
        order = {
            "schema_version": "1.0",
            "public_order_id": self.id_allocator_service.allocate("public_order"),
            "public_buyer_id": public_buyer_id,
            "buyer_email": buyer.get("email", ""),
            "items": items,
            "total_amount": float(cart.get("payment_required", 0)),
            "payment_mode": self._payment_config().get("mode", "UPI_MANUAL"),
            "payment_status": "PENDING",
            "payment_reference": "",
            "payment_screenshot_placeholder": "",
            "status": "PAYMENT_PENDING",
            "assigned_seller_manufacturer_id": seller_id,
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
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self.safe_drive_write_service.replace_document(self._order_path(order["public_order_id"], order["created_at"]), order)
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
        )
        self.gmail_service.enqueue_message(
            buyer.get("email", ""),
            f"Payment instructions for {order['public_order_id']}",
            self.build_payment_instruction_text(order),
            "public_order_created",
        )
        self.public_cart_service.clear_cart(public_buyer_id)
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
            payload["payment_status"] = "SUBMITTED"
            payload["updated_at"] = datetime.now(UTC).isoformat()
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator)
        updated = self.get_order(public_order_id)
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
            )
        self._record_payment_event(public_order_id, "PAYMENT_SUBMITTED", {"payment_reference": reference})
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
                payload["updated_at"] = datetime.now(UTC).isoformat()
                return payload
            self.safe_drive_write_service.mutate_json(path, reject_mutator)
            self._record_payment_event(public_order_id, "PAYMENT_REJECTED", {"note": note.strip()})
            return self.get_order(public_order_id)

        reserve_items = [{"product_id": item["product_id"], "qty": int(item["qty"])} for item in order.get("items", [])]
        self.dual_inventory_service.reserve_self_inventory(order["assigned_seller_manufacturer_id"], reserve_items)

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload["payment_status"] = "VERIFIED"
            payload["status"] = "PAID"
            payload["inventory_reserved"] = True
            payload["seller_note"] = note.strip()
            payload["updated_at"] = datetime.now(UTC).isoformat()
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator)
        updated = self.get_order(public_order_id)
        self.notification_center_service.create_public_notification(
            updated["public_buyer_id"],
            user_id=updated.get("buyer_email", ""),
            notification_type="PUBLIC_PAYMENT_VERIFIED",
            priority="SUCCESS",
            title="Payment verified",
            message=f"Your payment for {public_order_id} was verified.",
            source_type="PUBLIC_ORDER",
            source_id=public_order_id,
        )
        self.gmail_service.enqueue_message(
            updated.get("buyer_email", ""),
            f"Payment received for {public_order_id}",
            f"Payment for your public order {public_order_id} was verified successfully.",
            "public_payment_verified",
        )
        self._record_payment_event(public_order_id, "PAYMENT_VERIFIED", {"note": note.strip()})
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
        return self._transition_order(
            public_order_id,
            allowed_statuses={"CONFIRMED"},
            next_status="DISPATCHED",
            buyer_notification=("PUBLIC_ORDER_DISPATCHED", "Public order dispatched", f"Your public order {public_order_id} was dispatched."),
            buyer_email_subject=f"Dispatch update: {public_order_id}",
            buyer_email_body=f"Your public marketplace order {public_order_id} has been dispatched.",
        )

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
        )
        updated = self._transition_order(
            public_order_id,
            allowed_statuses={"DISPATCHED"},
            next_status="DELIVERED",
            buyer_notification=("PUBLIC_ORDER_DELIVERED", "Public order delivered", f"Your public order {public_order_id} is marked delivered."),
            buyer_email_subject=f"Delivery complete: {public_order_id}",
            buyer_email_body=f"Your public marketplace order {public_order_id} has been marked delivered.",
        )
        return updated

    def get_order(self, public_order_id: str) -> dict[str, Any]:
        for order in self.list_all_orders():
            if order.get("public_order_id") == public_order_id:
                return order
        raise ValueError(f"Public order not found: {public_order_id}")

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
        )
        self.gmail_service.enqueue_message(updated.get("buyer_email", ""), buyer_email_subject, buyer_email_body, notification_type.lower())
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
