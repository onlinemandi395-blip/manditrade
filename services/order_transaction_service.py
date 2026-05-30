from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class OrderTransactionContext:
    transaction_id: str
    state: str = "PENDING"
    order_id: str = ""
    affected_files: list[str] = field(default_factory=list)
    backup_targets: list[Path] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    error_message: str = ""


class OrderTransactionService:
    def __init__(
        self,
        drive_service,
        safe_drive_write_service,
        rollback_service,
        order_state_service,
        delivery_service,
        gmail_service,
        audit_service,
        logging_service,
        event_dispatcher,
        transactions_root: Path,
        id_allocator_service,
        dual_inventory_service,
        trade_confirmation_service,
        ledger_service,
        notification_center_service,
        domain_paths_service,
        pricing_service=None,
        procurement_transaction_service=None,
    ) -> None:
        self.drive_service = drive_service
        self.safe_drive_write_service = safe_drive_write_service
        self.rollback_service = rollback_service
        self.order_state_service = order_state_service
        self.delivery_service = delivery_service
        self.gmail_service = gmail_service
        self.audit_service = audit_service
        self.logging_service = logging_service
        self.event_dispatcher = event_dispatcher
        self.transactions_root = transactions_root
        self.id_allocator_service = id_allocator_service
        self.dual_inventory_service = dual_inventory_service
        self.trade_confirmation_service = trade_confirmation_service
        self.ledger_service = ledger_service
        self.notification_center_service = notification_center_service
        self.domain_paths = domain_paths_service
        self.pricing_service = pricing_service
        self.procurement_transaction_service = procurement_transaction_service

    def _journal_path(self, transaction_id: str) -> Path:
        return self.transactions_root / f"{transaction_id}.json"

    def _write_journal(self, context: OrderTransactionContext) -> None:
        self.transactions_root.mkdir(parents=True, exist_ok=True)
        self._journal_path(context.transaction_id).write_text(
            json.dumps(
                {
                    "transaction_id": context.transaction_id,
                    "state": context.state,
                    "order_id": context.order_id,
                    "affected_files": context.affected_files,
                    "backup_targets": [str(item) for item in context.backup_targets],
                    "created_at": context.created_at,
                    "error_message": context.error_message,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _register_target(self, context: OrderTransactionContext, target: Path) -> None:
        if target not in context.backup_targets:
            context.backup_targets.append(target)
            context.affected_files.append(str(target))
            self.safe_drive_write_service.backup_file(target)

    def _emit_event_safe(self, event_type: str, payload: dict[str, Any]) -> None:
        try:
            self.event_dispatcher.emit(event_type, payload, producer="OrderTransactionService")
        except Exception as exc:  # noqa: BLE001
            self.logging_service.log_error("event_failures", "Order event emission failed after commit", {"event_type": event_type, "error": str(exc)})

    def _enqueue_safe(self, *, to_email: str, subject: str, body: str, notification_type: str) -> None:
        try:
            self.gmail_service.enqueue_message(to_email=to_email, subject=subject, body=body, notification_type=notification_type)
        except Exception as exc:  # noqa: BLE001
            self.logging_service.log_error("notification_failures", "Side effect failed after order commit", {"notification_type": notification_type, "error": str(exc)})

    def _shared_order_projection(self, order: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": order.get("schema_version", "2.0"),
            "order_id": order["order_id"],
            "manufacturer_id": order.get("manufacturer_id", ""),
            "primary_manufacturer_id": order.get("primary_manufacturer_id", ""),
            "status": order.get("status", ""),
            "created_at": order.get("created_at", ""),
            "created_at_runtime": order.get("created_at_runtime", ""),
            "rfq_id": order.get("rfq_id", ""),
            "trade_confirmation_id": order.get("trade_confirmation_id", ""),
            "item_count": len(order.get("items", [])),
            "total_amount": round(
                sum(float(item.get("qty", 0)) * float(item.get("client_price", item.get("mrp", 0)) or 0) for item in order.get("items", [])),
                2,
            ),
            "items": [
                {
                    "product_id": item.get("product_id", ""),
                    "product_name": item.get("product_name", ""),
                    "qty": item.get("qty", 0),
                    "unit": item.get("unit", ""),
                    "channel": item.get("channel", "PRIVATE_CLIENT"),
                }
                for item in order.get("items", [])
            ],
        }

    def _projection_path_for_order(self, manufacturer_code: str, order: dict[str, Any]) -> Path:
        created_at = str(order.get("created_at") or datetime.now(UTC).date().isoformat())
        year_month = created_at[:7]
        return self.domain_paths.shared_client_order_projection_path(manufacturer_code, year_month, order["order_id"])

    def _save_order(self, manufacturer_code: str, order: dict[str, Any], order_path: Path) -> None:
        order.setdefault("schema_version", "2.0")
        self.safe_drive_write_service.replace_document(order_path, self._shared_order_projection(order))
        self.safe_drive_write_service.replace_document(self.domain_paths.client_order_path(manufacturer_code, order["order_id"]), order, schema_name="order")

    def _find_order_path(self, manufacturer_code: str, order_id: str) -> Path:
        private_path = self.domain_paths.client_order_path(manufacturer_code, order_id)
        if private_path.exists():
            return private_path
        raise FileNotFoundError(f"Order not found: {order_id}")

    def create_order(self, manufacturer_code: str, client_profile: dict[str, Any], items: list[dict[str, Any]], payment_proposal: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(UTC)
        transaction_id = self.id_allocator_service.allocate("transaction")
        order_id = self.id_allocator_service.allocate("order")
        order_path = self.domain_paths.shared_client_order_projection_path(manufacturer_code, now.strftime("%Y-%m"), order_id)
        context = OrderTransactionContext(transaction_id=transaction_id, state="RUNNING", order_id=order_id)
        self._write_journal(context)
        normalized_items = []
        commission_rows = []
        for item in items:
            client_price = float(item.get("client_price", item.get("mrp", 0)) or 0)
            mandi_price = float(item.get("mandi_price", 0) or 0)
            if self.pricing_service:
                commission_rows.append(
                    self.pricing_service.calculate_commission(
                        {"mandi_price": mandi_price, "client_price": client_price},
                        self.pricing_service.CHANNEL_PRIVATE_CLIENT,
                        client_profile.get("subscription_plan", "basic"),
                    )
                )
            normalized_items.append(
                {
                    **item,
                    "client_price": client_price,
                    "sale_price": client_price,
                    "mrp": client_price,
                    "mandi_price": mandi_price,
                    "channel": "PRIVATE_CLIENT",
                }
            )
        order = {
            "schema_version": "2.0",
            "order_id": order_id,
            "client_id": client_profile["client_id"],
            "client_email": client_profile["email"],
            "manufacturer_id": manufacturer_code,
            "primary_manufacturer_id": manufacturer_code,
            "items": normalized_items,
            "payment_proposal": payment_proposal,
            "status": "PROPOSED",
            "created_at": now.date().isoformat(),
            "created_at_runtime": now.isoformat(),
            "status_history": [],
            "transaction_id": transaction_id,
            "commission_breakdown": commission_rows,
        }
        try:
            self._register_target(context, self.domain_paths.private_self_inventory_path(manufacturer_code))
            self._register_target(context, order_path)
            self._register_target(context, self.domain_paths.client_order_path(manufacturer_code, order_id))
            inventory = self.dual_inventory_service.list_inventory(manufacturer_code)
            shortages = []
            for item in items:
                record = next((entry for entry in inventory.get("items", []) if entry.get("product_id") == item["product_id"]), None)
                available = 0 if record is None else int(record["self_inventory"].get("available_qty", 0)) - int(record["self_inventory"].get("reserved_qty", 0))
                if available < int(item["qty"]):
                    shortages.append({"product_id": item["product_id"], "required_qty": int(item["qty"]) - max(0, available), "unit": item["unit"]})
            if shortages:
                order = self.order_state_service.transition(order, "PROCUREMENT_REQUIRED", client_profile["email"], reason="Self inventory shortage detected")
                if self.procurement_transaction_service is not None:
                    rfq = self.procurement_transaction_service.create_rfq_from_shortage(
                        manufacturer_code=manufacturer_code,
                        items=shortages,
                        trade_terms=payment_proposal,
                    )
                    order["rfq_id"] = rfq["rfq_id"]
                    self.notification_center_service.create_notification(
                        manufacturer_code,
                        user_id=manufacturer_code,
                        notification_type="RFQ_CREATED",
                        priority="HIGH",
                        title="RFQ Created",
                        message="Inventory shortage moved into mandi RFQ.",
                        source_type="RFQ",
                        source_id=rfq["rfq_id"],
                    )
            else:
                self.dual_inventory_service.reserve_self_inventory(manufacturer_code, items)
                order = self.order_state_service.transition(order, "MANUFACTURER_ACCEPTED", client_profile["email"], reason="Self inventory reserved")
                order = self.order_state_service.transition(order, "READY_TO_CONFIRM", client_profile["email"], reason="Order ready for confirmation")
            self._save_order(manufacturer_code, order, order_path)
            context.state = "COMMITTED"
            self._write_journal(context)
        except Exception as exc:  # noqa: BLE001
            context.state = "ROLLED_BACK"
            context.error_message = str(exc)
            self.rollback_service.restore_files(context.backup_targets)
            self._write_journal(context)
            raise
        self._emit_event_safe("ORDER_CREATED", {"transaction_id": transaction_id, "correlation_id": order_id, "order_id": order_id})
        self._enqueue_safe(to_email=client_profile["email"], subject="Order Proposed", body=f"Order {order_id} submitted with status {order['status']}.", notification_type="order_placed")
        return order

    def confirm_order(self, current_user, order_id: str) -> dict[str, Any]:
        transaction_id = self.id_allocator_service.allocate("transaction")
        order_path = self._find_order_path(current_user.manufacturer_code, order_id)
        context = OrderTransactionContext(transaction_id=transaction_id, state="RUNNING", order_id=order_id)
        self._write_journal(context)
        try:
            self._register_target(context, self.domain_paths.client_order_path(current_user.manufacturer_code, order_id))
            projection_path = self._projection_path_for_order(current_user.manufacturer_code, self.drive_service.json_service.read_json(order_path, {}))
            self._register_target(context, projection_path)
            self._register_target(context, self.domain_paths.confirmations_path(current_user.manufacturer_code))
            order = self.drive_service.json_service.read_json(order_path, {})
            order = self.order_state_service.transition(order, "CONFIRMED", current_user.email, reason="Manufacturer confirmed order")
            confirmation = self.trade_confirmation_service.create_confirmation(
                current_user.manufacturer_code,
                source_type="CLIENT_ORDER",
                source_id=order_id,
                confirmed_by=current_user.email,
                accepted_terms_snapshot={"payment_proposal": order.get("payment_proposal", {}), "items": order.get("items", [])},
            )
            order["trade_confirmation_id"] = confirmation["confirmation_id"]
            self._save_order(current_user.manufacturer_code, order, projection_path)
            ledger_amount = sum(float(item.get("qty", 0)) * float(item.get("client_price", item.get("mrp", 0))) for item in order.get("items", []))
            proposal = order.get("payment_proposal", {})
            upfront = round(ledger_amount * float(proposal.get("upfront_percentage", 0)) / 100, 2)
            self.ledger_service.create_entry(
                current_user.manufacturer_code,
                party_a=current_user.manufacturer_code,
                party_b=order["client_id"],
                entry_type="ORDER_SUPPLIED",
                amount=ledger_amount,
                paid_amount=upfront,
                ledger_days=int(proposal.get("ledger_days", 0)),
                note=proposal.get("freestyle_note", ""),
                metadata={
                    "channel": "PRIVATE_CLIENT",
                    "mandi_price": sum(float(item.get("qty", 0)) * float(item.get("mandi_price", 0)) for item in order.get("items", [])),
                    "sale_price": ledger_amount,
                    "gross_profit": sum(float(item.get("qty", 0)) * (float(item.get("client_price", item.get("mrp", 0))) - float(item.get("mandi_price", 0))) for item in order.get("items", [])),
                    "commission_breakdown": order.get("commission_breakdown", {}),
                },
            )
            context.state = "COMMITTED"
            self._write_journal(context)
        except Exception as exc:  # noqa: BLE001
            context.state = "ROLLED_BACK"
            context.error_message = str(exc)
            self.rollback_service.restore_files(context.backup_targets)
            self._write_journal(context)
            raise
        self._emit_event_safe("ORDER_CONFIRMED", {"transaction_id": transaction_id, "correlation_id": order_id, "order_id": order_id})
        return order

    def dispatch_order(self, current_user, order_id: str, vehicle_number: str, driver_name: str, transporter_name: str, proof_file=None) -> dict[str, Any]:
        transaction_id = self.id_allocator_service.allocate("transaction")
        order_path = self._find_order_path(current_user.manufacturer_code, order_id)
        context = OrderTransactionContext(transaction_id=transaction_id, state="RUNNING", order_id=order_id)
        self._write_journal(context)
        try:
            self._register_target(context, self.domain_paths.client_order_path(current_user.manufacturer_code, order_id))
            projection_path = self._projection_path_for_order(current_user.manufacturer_code, self.drive_service.json_service.read_json(order_path, {}))
            self._register_target(context, projection_path)
            order = self.drive_service.json_service.read_json(order_path, {})
            if order.get("status") != "CONFIRMED":
                raise ValueError("Order must be CONFIRMED before dispatch.")
            dispatch = self.delivery_service.build_dispatch_record(order_id, vehicle_number, driver_name, transporter_name)
            order["dispatch"] = dispatch
            order = self.order_state_service.transition(order, "DISPATCHED", current_user.email, reason="Shipment dispatched")
            self._save_order(current_user.manufacturer_code, order, projection_path)
            context.state = "COMMITTED"
            self._write_journal(context)
        except Exception as exc:  # noqa: BLE001
            context.state = "ROLLED_BACK"
            context.error_message = str(exc)
            self.rollback_service.restore_files(context.backup_targets)
            self._write_journal(context)
            raise
        return order

    def confirm_delivery(self, current_user, order_id: str, comments: str = "", proof_file=None) -> dict[str, Any]:
        transaction_id = self.id_allocator_service.allocate("transaction")
        order_path = self._find_order_path(current_user.manufacturer_code, order_id)
        context = OrderTransactionContext(transaction_id=transaction_id, state="RUNNING", order_id=order_id)
        self._write_journal(context)
        try:
            self._register_target(context, self.domain_paths.client_order_path(current_user.manufacturer_code, order_id))
            projection_path = self._projection_path_for_order(current_user.manufacturer_code, self.drive_service.json_service.read_json(order_path, {}))
            self._register_target(context, projection_path)
            self._register_target(context, self.domain_paths.private_self_inventory_path(current_user.manufacturer_code))
            order = self.drive_service.json_service.read_json(order_path, {})
            if order.get("status") != "DISPATCHED":
                raise ValueError("Order must be DISPATCHED before delivery confirmation.")
            order = self.delivery_service.confirm_delivery(order, current_user.email, comments=comments, proof_path=None)
            order = self.order_state_service.transition(order, "DELIVERED", current_user.email, reason="Delivery confirmed")
            self.dual_inventory_service.finalize_reserved(current_user.manufacturer_code, order.get("items", []), bucket="self_inventory")
            self._save_order(current_user.manufacturer_code, order, projection_path)
            context.state = "COMMITTED"
            self._write_journal(context)
        except Exception as exc:  # noqa: BLE001
            context.state = "ROLLED_BACK"
            context.error_message = str(exc)
            self.rollback_service.restore_files(context.backup_targets)
            self._write_journal(context)
            raise
        return order

    def close_order(self, current_user, order_id: str, reason: str = "") -> dict[str, Any]:
        return self._simple_transition(current_user, order_id, "CLOSED", reason or "Order closed")

    def cancel_order(self, current_user, order_id: str, reason: str = "") -> dict[str, Any]:
        transaction_id = self.id_allocator_service.allocate("transaction")
        order_path = self._find_order_path(current_user.manufacturer_code, order_id)
        context = OrderTransactionContext(transaction_id=transaction_id, state="RUNNING", order_id=order_id)
        self._write_journal(context)
        try:
            self._register_target(context, self.domain_paths.client_order_path(current_user.manufacturer_code, order_id))
            projection_path = self._projection_path_for_order(current_user.manufacturer_code, self.drive_service.json_service.read_json(order_path, {}))
            self._register_target(context, projection_path)
            self._register_target(context, self.domain_paths.private_self_inventory_path(current_user.manufacturer_code))
            order = self.drive_service.json_service.read_json(order_path, {})
            if order.get("status") in {"MANUFACTURER_ACCEPTED", "READY_TO_CONFIRM", "CONFIRMED"}:
                self.dual_inventory_service.release_reserved(current_user.manufacturer_code, order.get("items", []), bucket="self_inventory")
            order = self.order_state_service.transition(order, "CANCELLED", current_user.email, reason=reason or "Order cancelled")
            self._save_order(current_user.manufacturer_code, order, projection_path)
            context.state = "COMMITTED"
            self._write_journal(context)
        except Exception as exc:  # noqa: BLE001
            context.state = "ROLLED_BACK"
            context.error_message = str(exc)
            self.rollback_service.restore_files(context.backup_targets)
            self._write_journal(context)
            raise
        return order

    def _simple_transition(self, current_user, order_id: str, next_status: str, reason: str) -> dict[str, Any]:
        transaction_id = self.id_allocator_service.allocate("transaction")
        order_path = self._find_order_path(current_user.manufacturer_code, order_id)
        context = OrderTransactionContext(transaction_id=transaction_id, state="RUNNING", order_id=order_id)
        self._write_journal(context)
        try:
            self._register_target(context, self.domain_paths.client_order_path(current_user.manufacturer_code, order_id))
            projection_path = self._projection_path_for_order(current_user.manufacturer_code, self.drive_service.json_service.read_json(order_path, {}))
            self._register_target(context, projection_path)
            order = self.drive_service.json_service.read_json(order_path, {})
            order = self.order_state_service.transition(order, next_status, current_user.email, reason=reason)
            self._save_order(current_user.manufacturer_code, order, projection_path)
            context.state = "COMMITTED"
            self._write_journal(context)
        except Exception as exc:  # noqa: BLE001
            context.state = "ROLLED_BACK"
            context.error_message = str(exc)
            self.rollback_service.restore_files(context.backup_targets)
            self._write_journal(context)
            raise
        return order

    def recover_incomplete_transactions(self) -> list[dict[str, Any]]:
        recovered = []
        self.transactions_root.mkdir(parents=True, exist_ok=True)
        for path in self.transactions_root.glob("TXN-*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("state") in {"PENDING", "RUNNING", "FAILED"}:
                self.rollback_service.restore_files([Path(item) for item in payload.get("backup_targets", [])])
                payload["state"] = "ROLLED_BACK"
                path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                recovered.append(payload)
        return recovered
