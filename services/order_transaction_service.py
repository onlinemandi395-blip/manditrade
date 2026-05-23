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
    rollback_cleanup_files: list[Path] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    error_message: str = ""


class OrderTransactionService:
    def __init__(
        self,
        drive_service,
        safe_drive_write_service,
        rollback_service,
        order_state_service,
        agreement_service,
        agreement_settlement_service,
        delivery_service,
        gmail_service,
        audit_service,
        logging_service,
        event_dispatcher,
        transactions_root: Path,
        id_allocator_service,
    ) -> None:
        self.drive_service = drive_service
        self.safe_drive_write_service = safe_drive_write_service
        self.rollback_service = rollback_service
        self.order_state_service = order_state_service
        self.agreement_service = agreement_service
        self.agreement_settlement_service = agreement_settlement_service
        self.delivery_service = delivery_service
        self.gmail_service = gmail_service
        self.audit_service = audit_service
        self.logging_service = logging_service
        self.event_dispatcher = event_dispatcher
        self.transactions_root = transactions_root
        self.id_allocator_service = id_allocator_service

    def _emit_event_safe(self, event_type: str, payload: dict[str, Any]) -> None:
        try:
            self.event_dispatcher.emit(event_type, payload, producer="OrderTransactionService")
        except Exception as exc:  # noqa: BLE001
            self.logging_service.log_error(
                "event_failures",
                "Order event emission failed after commit",
                {"event_type": event_type, "payload": payload, "error": str(exc)},
            )

    def _enqueue_safe(self, *, to_email: str, subject: str, body: str, notification_type: str, transaction_id: str, order_id: str) -> None:
        try:
            self.gmail_service.enqueue_message(
                to_email=to_email,
                subject=subject,
                body=body,
                notification_type=notification_type,
            )
        except Exception as exc:  # noqa: BLE001
            self.logging_service.log_error(
                "notification_failures",
                "Side effect failed after order commit",
                {"transaction_id": transaction_id, "order_id": order_id, "notification_type": notification_type, "error": str(exc)},
            )

    def _quarantine_corrupted_journal(self, path: Path, error: str) -> dict[str, Any]:
        quarantine_dir = self.transactions_root / "quarantine"
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        target = quarantine_dir / path.name
        path.replace(target)
        payload = {
            "transaction_id": path.stem,
            "state": "CORRUPTED",
            "error_message": error,
            "quarantined_path": str(target),
        }
        self.logging_service.log_error(
            "transaction_failures",
            "Corrupted order journal quarantined",
            payload,
        )
        return payload

    def _journal_path(self, transaction_id: str) -> Path:
        return self.transactions_root / f"{transaction_id}.json"

    def _write_journal(self, context: OrderTransactionContext) -> None:
        self.transactions_root.mkdir(parents=True, exist_ok=True)
        payload = {
            "transaction_id": context.transaction_id,
            "state": context.state,
            "order_id": context.order_id,
            "affected_files": context.affected_files,
            "backup_targets": [str(path) for path in context.backup_targets],
            "rollback_cleanup_files": [str(path) for path in context.rollback_cleanup_files],
            "created_at": context.created_at,
            "error_message": context.error_message,
        }
        self._journal_path(context.transaction_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _register_target(self, context: OrderTransactionContext, target: Path) -> None:
        if target not in context.backup_targets:
            context.backup_targets.append(target)
            context.affected_files.append(str(target))
            self.safe_drive_write_service.backup_file(target)

    def _find_order_path(self, manufacturer_code: str, order_id: str) -> Path:
        orders_root = self.drive_service.get_manufacturer_paths(manufacturer_code).shared_zone / "orders"
        for path in sorted(orders_root.glob("*/*.json")):
            if path.stem == order_id:
                return path
        raise FileNotFoundError(f"Order not found: {order_id}")

    def _client_order_path(self, manufacturer_code: str, order_id: str) -> Path:
        return self.drive_service.get_manufacturer_paths(manufacturer_code).private_zone / "client_orders" / f"{order_id}.json"

    def _agreements_path(self, manufacturer_code: str) -> Path:
        return self.drive_service.get_manufacturer_paths(manufacturer_code).shared_zone / "agreements.json"

    def _inventory_path(self, manufacturer_code: str) -> Path:
        return self.drive_service.get_manufacturer_paths(manufacturer_code).shared_zone / "inventory.json"

    def _save_order(self, manufacturer_code: str, order: dict[str, Any], order_path: Path) -> None:
        order.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(order_path, order, schema_name="order")
        self.safe_drive_write_service.replace_document(self._client_order_path(manufacturer_code, order["order_id"]), order, schema_name="order")

    def _update_agreement(self, manufacturer_code: str, agreement_id: str, updater) -> dict[str, Any]:
        agreements_path = self._agreements_path(manufacturer_code)
        agreements_doc = self.drive_service.json_service.read_json(agreements_path, {"schema_version": "1.0", "agreements": []})
        updated_agreement = None
        for index, agreement in enumerate(agreements_doc.get("agreements", [])):
            if agreement.get("agreement_id") == agreement_id:
                updated_agreement = updater(dict(agreement))
                agreements_doc["agreements"][index] = updated_agreement
                break
        if updated_agreement is None:
            raise ValueError(f"Agreement not found: {agreement_id}")
        self.safe_drive_write_service.replace_document(agreements_path, agreements_doc)
        return updated_agreement

    def _release_reserved_inventory(self, manufacturer_code: str, items: list[dict[str, Any]]) -> None:
        inventory_path = self._inventory_path(manufacturer_code)
        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload.setdefault("schema_version", "1.0")
            payload.setdefault("items", [])
            for item in items:
                record = next((entry for entry in payload["items"] if entry.get("product_code") == item["product_id"]), None)
                if record:
                    record["reserved_quantity"] = max(0, int(record.get("reserved_quantity", 0)) - int(item["qty"]))
            return payload
        self.safe_drive_write_service.mutate_json(inventory_path, mutator, schema_name="inventory")

    def _finalize_inventory(self, manufacturer_code: str, items: list[dict[str, Any]], transaction_id: str) -> None:
        inventory_path = self._inventory_path(manufacturer_code)
        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload.setdefault("schema_version", "1.0")
            payload.setdefault("items", [])
            for item in items:
                record = next((entry for entry in payload["items"] if entry.get("product_code") == item["product_id"]), None)
                if record:
                    qty = int(item["qty"])
                    record["reserved_quantity"] = max(0, int(record.get("reserved_quantity", 0)) - qty)
                    record["quantity"] = max(0, int(record.get("quantity", 0)) - qty)
                    record["last_transaction_id"] = transaction_id
            return payload
        self.safe_drive_write_service.mutate_json(inventory_path, mutator, schema_name="inventory")

    def create_order(self, manufacturer_code: str, client_profile: dict[str, Any], selected_product: dict[str, Any], qty: int) -> dict[str, Any]:
        now = datetime.now(UTC)
        transaction_id = self.id_allocator_service.allocate("transaction")
        order_id = self.id_allocator_service.allocate("order")
        item = {
            "product_id": selected_product["product_code"],
            "product_name": selected_product["product_name"],
            "qty": int(qty),
            "mrp": float(selected_product["mrp"]),
        }
        context = OrderTransactionContext(transaction_id=transaction_id, state="RUNNING", order_id=order_id)
        self._write_journal(context)
        order = {
            "schema_version": "1.0",
            "order_id": order_id,
            "client_id": client_profile["client_id"],
            "client_email": client_profile["email"],
            "manufacturer_id": manufacturer_code,
            "items": [item],
            "status": "PLACED",
            "created_at": now.date().isoformat(),
            "created_at_runtime": now.isoformat(),
            "status_history": [],
            "transaction_id": transaction_id,
        }
        actor = client_profile["email"]
        order_path = self.drive_service.resolve_orders_month_dir(manufacturer_code, now.strftime("%Y-%m")) / f"{order_id}.json"
        client_order_path = self._client_order_path(manufacturer_code, order_id)
        agreements_path = self._agreements_path(manufacturer_code)
        try:
            self._register_target(context, self._inventory_path(manufacturer_code))
            self._register_target(context, order_path)
            self._register_target(context, client_order_path)
            self._register_target(context, agreements_path)
            order = self.order_state_service.transition(order, "VALIDATED", actor, reason="Initial order validation started")
            validation = self.drive_service.json_service.read_json(self._inventory_path(manufacturer_code), {"items": []})
            record = next((entry for entry in validation.get("items", []) if entry.get("product_code") == item["product_id"]), None)
            available = int(record.get("quantity", 0) - record.get("reserved_quantity", 0)) if record else 0
            if available < int(item["qty"]):
                order = self.order_state_service.transition(order, "PROCUREMENT_REQUIRED", actor, reason="Inventory shortage detected")
            else:
                self.safe_drive_write_service.mutate_json(
                    self._inventory_path(manufacturer_code),
                    lambda payload: self._reserve_for_create(payload, manufacturer_code, [item], transaction_id),
                    schema_name="inventory",
                )
                order = self.order_state_service.transition(order, "CONFIRMED", actor, reason="Inventory reserved")
                order = self.order_state_service.transition(order, "AGREEMENT_PENDING", actor, reason="Agreement generation started")
                agreement = self.agreement_service.create_order_agreement(
                    order_id=order_id,
                    manufacturer_id=manufacturer_code,
                    client_id=client_profile["client_id"],
                    items=order["items"],
                    total_amount=qty * float(selected_product["mrp"]),
                )
                agreement["transaction_id"] = transaction_id
                agreement["status"] = "ADVANCE_PENDING"
                pdf_path = self.agreement_service.generate_pdf(
                    agreement,
                    self.drive_service.get_manufacturer_paths(manufacturer_code).private_zone / "invoices" / f"{agreement['agreement_id']}.pdf",
                )
                agreement["pdf_path"] = str(pdf_path)
                context.rollback_cleanup_files.append(pdf_path)
                order["agreement_id"] = agreement["agreement_id"]
                order = self.order_state_service.transition(order, "ADVANCE_PENDING", actor, reason="Advance payment required")
                if not agreements_path.exists():
                    self.safe_drive_write_service.replace_document(
                        agreements_path,
                        {"schema_version": "1.0", "manufacturer_code": manufacturer_code, "agreements": []},
                    )
                self.safe_drive_write_service.append_record(agreements_path, "agreements", {"schema_version": "1.0", **agreement})
            self._save_order(manufacturer_code, order, order_path)
            context.state = "COMMITTED"
            self._write_journal(context)
            self.audit_service.log_event(
                "order_created",
                actor=actor,
                details={"transaction_id": transaction_id, "order_id": order_id, "status": order["status"]},
            )
            self._emit_event_safe(
                "ORDER_CREATED",
                {"transaction_id": transaction_id, "correlation_id": order_id, "order_id": order_id, "manufacturer_id": manufacturer_code},
            )
        except Exception as exc:  # noqa: BLE001
            context.state = "ROLLED_BACK"
            context.error_message = str(exc)
            self.rollback_service.restore_files(context.backup_targets)
            for file_path in context.rollback_cleanup_files:
                self.rollback_service.remove_file_if_exists(file_path)
            self._write_journal(context)
            raise
        if order["status"] != "PROCUREMENT_REQUIRED":
            self._enqueue_safe(
                to_email=client_profile["email"],
                subject="Order Confirmed",
                body=f"Order {order_id} is confirmed. Advance pending for agreement {order.get('agreement_id', '')}.",
                notification_type="order_confirmed",
                transaction_id=transaction_id,
                order_id=order_id,
            )
        self._enqueue_safe(
            to_email=client_profile["email"],
            subject="Order Placed",
            body=f"Order {order_id} has been placed with status {order['status']}.",
            notification_type="order_placed",
            transaction_id=transaction_id,
            order_id=order_id,
        )
        return order

    def _reserve_for_create(self, payload: dict[str, Any], manufacturer_code: str, items: list[dict[str, Any]], transaction_id: str) -> dict[str, Any]:
        payload.setdefault("schema_version", "1.0")
        payload.setdefault("manufacturer_code", manufacturer_code)
        payload.setdefault("items", [])
        for item in items:
            record = next((entry for entry in payload["items"] if entry.get("product_code") == item["product_id"]), None)
            if record:
                available = int(record.get("quantity", 0) - record.get("reserved_quantity", 0))
                if available < int(item["qty"]):
                    raise ValueError("Inventory changed before order commit.")
                record["reserved_quantity"] = int(record.get("reserved_quantity", 0)) + int(item["qty"])
                record["last_transaction_id"] = transaction_id
            else:
                raise ValueError(f"Inventory record not found for {item['product_id']}")
        return payload

    def mark_dispatch_ready(self, current_user, order_id: str) -> dict[str, Any]:
        return self._simple_order_transition(current_user, order_id, "DISPATCH_READY", "Advance verified and shipment prepared", "ORDER_CONFIRMED")

    def dispatch_order(self, current_user, order_id: str, vehicle_number: str, driver_name: str, transporter_name: str, proof_file=None) -> dict[str, Any]:
        transaction_id = self.id_allocator_service.allocate("transaction")
        order_path = self._find_order_path(current_user.manufacturer_code, order_id)
        context = OrderTransactionContext(transaction_id=transaction_id, state="RUNNING", order_id=order_id)
        self._write_journal(context)
        try:
            order = self.drive_service.json_service.read_json(order_path, {})
            if order.get("status") != "DISPATCH_READY":
                raise ValueError("Order must be DISPATCH_READY before dispatch.")
            self._register_target(context, order_path)
            dispatch = self.delivery_service.build_dispatch_record(order_id, vehicle_number, driver_name, transporter_name)
            dispatch["transaction_id"] = transaction_id
            proofs_dir = self.drive_service.get_manufacturer_paths(current_user.manufacturer_code).private_zone / "delivery_proofs"
            if proof_file is not None:
                proof_path = self.delivery_service.save_delivery_proof(proofs_dir, order_id, proof_file)
                dispatch["proof_images"].append(proof_path)
                context.rollback_cleanup_files.append(Path(proof_path))
            order["dispatch"] = dispatch
            order = self.order_state_service.transition(order, "DISPATCHED", current_user.email, reason="Shipment dispatched")
            order["transaction_id"] = transaction_id
            self._save_order(current_user.manufacturer_code, order, order_path)
            context.state = "COMMITTED"
            self._write_journal(context)
            self.audit_service.log_event("order_dispatch_committed", actor=current_user.email, details={"transaction_id": transaction_id, "order_id": order_id})
        except Exception as exc:  # noqa: BLE001
            context.state = "ROLLED_BACK"
            context.error_message = str(exc)
            self.rollback_service.restore_files(context.backup_targets)
            for file_path in context.rollback_cleanup_files:
                self.rollback_service.remove_file_if_exists(file_path)
            self._write_journal(context)
            raise
        self._emit_event_safe("ORDER_DISPATCHED", {"transaction_id": transaction_id, "correlation_id": order_id, "order_id": order_id})
        self._enqueue_safe(
            to_email=order["client_email"],
            subject="Dispatch Update",
            body=f"Order {order_id} has been dispatched via {transporter_name or 'assigned transporter'}.",
            notification_type="dispatch_update",
            transaction_id=transaction_id,
            order_id=order_id,
        )
        return order

    def confirm_delivery(self, current_user, order_id: str, comments: str = "", proof_file=None) -> dict[str, Any]:
        transaction_id = self.id_allocator_service.allocate("transaction")
        order_path = self._find_order_path(current_user.manufacturer_code, order_id)
        context = OrderTransactionContext(transaction_id=transaction_id, state="RUNNING", order_id=order_id)
        self._write_journal(context)
        try:
            order = self.drive_service.json_service.read_json(order_path, {})
            if order.get("status") != "DISPATCHED":
                raise ValueError("Order must be DISPATCHED before delivery confirmation.")
            self._register_target(context, order_path)
            self._register_target(context, self._inventory_path(current_user.manufacturer_code))
            if order.get("agreement_id"):
                self._register_target(context, self._agreements_path(current_user.manufacturer_code))
            proofs_dir = self.drive_service.get_manufacturer_paths(current_user.manufacturer_code).private_zone / "delivery_proofs"
            proof_path = None
            if proof_file is not None:
                proof_path = self.delivery_service.save_delivery_proof(proofs_dir, order_id, proof_file)
                context.rollback_cleanup_files.append(Path(proof_path))
            order = self.delivery_service.confirm_delivery(order, current_user.email, comments=comments, proof_path=proof_path)
            order = self.order_state_service.transition(order, "DELIVERED", current_user.email, reason="Delivery confirmed")
            self._finalize_inventory(current_user.manufacturer_code, order.get("items", []), transaction_id)
            if order.get("agreement_id"):
                self._update_agreement(
                    current_user.manufacturer_code,
                    order["agreement_id"],
                    lambda agreement: self.agreement_service.update_status(agreement, "CLOSED"),
                )
            order["transaction_id"] = transaction_id
            self._save_order(current_user.manufacturer_code, order, order_path)
            context.state = "COMMITTED"
            self._write_journal(context)
            self.audit_service.log_event("order_delivery_committed", actor=current_user.email, details={"transaction_id": transaction_id, "order_id": order_id})
        except Exception as exc:  # noqa: BLE001
            context.state = "ROLLED_BACK"
            context.error_message = str(exc)
            self.rollback_service.restore_files(context.backup_targets)
            for file_path in context.rollback_cleanup_files:
                self.rollback_service.remove_file_if_exists(file_path)
            self._write_journal(context)
            raise
        self._emit_event_safe("ORDER_DELIVERED", {"transaction_id": transaction_id, "correlation_id": order_id, "order_id": order_id})
        self._enqueue_safe(
            to_email=order["client_email"],
            subject="Delivery Confirmed",
            body=f"Order {order_id} delivery has been confirmed.",
            notification_type="delivery_confirmation",
            transaction_id=transaction_id,
            order_id=order_id,
        )
        return order

    def close_order(self, current_user, order_id: str, reason: str = "") -> dict[str, Any]:
        order = self._simple_order_transition(current_user, order_id, "CLOSED", reason or "Order closed", "ORDER_CLOSED")
        if order.get("agreement_id"):
            self._update_agreement(
                current_user.manufacturer_code,
                order["agreement_id"],
                lambda agreement: self.agreement_settlement_service.confirm_settlement(
                    agreement,
                    float(agreement.get("advance_received", agreement.get("advance_amount", 0))),
                    current_user.email,
                ),
            )
        return order

    def cancel_order(self, current_user, order_id: str, reason: str = "") -> dict[str, Any]:
        transaction_id = self.id_allocator_service.allocate("transaction")
        order_path = self._find_order_path(current_user.manufacturer_code, order_id)
        context = OrderTransactionContext(transaction_id=transaction_id, state="RUNNING", order_id=order_id)
        self._write_journal(context)
        try:
            order = self.drive_service.json_service.read_json(order_path, {})
            self._register_target(context, order_path)
            self._register_target(context, self._inventory_path(current_user.manufacturer_code))
            if order.get("agreement_id"):
                self._register_target(context, self._agreements_path(current_user.manufacturer_code))
            self._release_reserved_inventory(current_user.manufacturer_code, order.get("items", []))
            if order.get("agreement_id"):
                self._update_agreement(
                    current_user.manufacturer_code,
                    order["agreement_id"],
                    lambda agreement: self.agreement_service.update_status(agreement, "CANCELLED"),
                )
            order = self.order_state_service.transition(order, "CANCELLED", current_user.email, reason=reason or "Order cancelled")
            order["transaction_id"] = transaction_id
            self._save_order(current_user.manufacturer_code, order, order_path)
            context.state = "COMMITTED"
            self._write_journal(context)
        except Exception as exc:  # noqa: BLE001
            context.state = "ROLLED_BACK"
            context.error_message = str(exc)
            self.rollback_service.restore_files(context.backup_targets)
            self._write_journal(context)
            raise
        self._emit_event_safe("ORDER_CLOSED", {"transaction_id": transaction_id, "correlation_id": order_id, "order_id": order_id, "cancelled": True})
        return order

    def confirm_order(self, current_user, order_id: str) -> dict[str, Any]:
        return self._simple_order_transition(current_user, order_id, "CONFIRMED", "Order confirmed", "ORDER_CONFIRMED")

    def _simple_order_transition(self, current_user, order_id: str, next_status: str, reason: str, event_type: str) -> dict[str, Any]:
        transaction_id = self.id_allocator_service.allocate("transaction")
        order_path = self._find_order_path(current_user.manufacturer_code, order_id)
        context = OrderTransactionContext(transaction_id=transaction_id, state="RUNNING", order_id=order_id)
        self._write_journal(context)
        try:
            self._register_target(context, order_path)
            order = self.drive_service.json_service.read_json(order_path, {})
            order = self.order_state_service.transition(order, next_status, current_user.email, reason=reason)
            order["transaction_id"] = transaction_id
            self._save_order(current_user.manufacturer_code, order, order_path)
            context.state = "COMMITTED"
            self._write_journal(context)
        except Exception as exc:  # noqa: BLE001
            context.state = "ROLLED_BACK"
            context.error_message = str(exc)
            self.rollback_service.restore_files(context.backup_targets)
            self._write_journal(context)
            raise
        self._emit_event_safe(event_type, {"transaction_id": transaction_id, "correlation_id": order_id, "order_id": order_id})
        return order

    def recover_incomplete_transactions(self) -> list[dict[str, Any]]:
        recovered: list[dict[str, Any]] = []
        self.transactions_root.mkdir(parents=True, exist_ok=True)
        for path in self.transactions_root.glob("TXN-*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                recovered.append(self._quarantine_corrupted_journal(path, str(exc)))
                continue
            if payload.get("state") in {"PENDING", "RUNNING", "FAILED"}:
                self.rollback_service.restore_files([Path(item) for item in payload.get("backup_targets", [])])
                for item in payload.get("rollback_cleanup_files", []):
                    self.rollback_service.remove_file_if_exists(Path(item))
                payload["state"] = "ROLLED_BACK"
                path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                recovered.append(payload)
        return recovered
