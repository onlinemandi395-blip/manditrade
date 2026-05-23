from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class TransactionContext:
    transaction_id: str
    state: str = "PENDING"
    affected_files: list[str] = field(default_factory=list)
    backup_targets: list[Path] = field(default_factory=list)
    rollback_cleanup_files: list[Path] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    error_message: str = ""


class ProcurementTransactionService:
    def __init__(
        self,
        drive_service,
        agreement_service,
        safe_drive_write_service,
        rollback_service,
        order_validation_service,
        procurement_matching_service,
        gmail_service,
        audit_service,
        logging_service,
        transactions_root: Path,
        event_dispatcher,
        id_allocator_service,
    ) -> None:
        self.drive_service = drive_service
        self.agreement_service = agreement_service
        self.safe_drive_write_service = safe_drive_write_service
        self.rollback_service = rollback_service
        self.order_validation_service = order_validation_service
        self.procurement_matching_service = procurement_matching_service
        self.gmail_service = gmail_service
        self.audit_service = audit_service
        self.logging_service = logging_service
        self.transactions_root = transactions_root
        self.event_dispatcher = event_dispatcher
        self.id_allocator_service = id_allocator_service

    def _emit_event_safe(self, event_type: str, payload: dict[str, Any]) -> None:
        try:
            self.event_dispatcher.emit(event_type, payload, producer="ProcurementTransactionService")
        except Exception as exc:  # noqa: BLE001
            self.logging_service.log_error(
                "event_failures",
                "Procurement event emission failed after commit",
                {"event_type": event_type, "payload": payload, "error": str(exc)},
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
            "Corrupted procurement journal quarantined",
            payload,
        )
        return payload

    def _journal_path(self, transaction_id: str) -> Path:
        return self.transactions_root / f"{transaction_id}.json"

    def _write_journal(self, context: TransactionContext) -> None:
        self.transactions_root.mkdir(parents=True, exist_ok=True)
        payload = {
            "transaction_id": context.transaction_id,
            "state": context.state,
            "affected_files": context.affected_files,
            "backup_targets": [str(path) for path in context.backup_targets],
            "rollback_cleanup_files": [str(path) for path in context.rollback_cleanup_files],
            "created_at": context.created_at,
            "error_message": context.error_message,
        }
        self._journal_path(context.transaction_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _register_target(self, context: TransactionContext, target: Path) -> None:
        if target not in context.backup_targets:
            context.backup_targets.append(target)
            context.affected_files.append(str(target))
            self.safe_drive_write_service.backup_file(target)

    def accept_procurement_request(
        self,
        current_user,
        request_id: str,
        unit_price: float,
        advance_amount: float,
    ) -> dict[str, Any]:
        transaction_id = self.id_allocator_service.allocate("transaction")
        context = TransactionContext(transaction_id=transaction_id, state="RUNNING")
        self._write_journal(context)

        own_paths = self.drive_service.get_manufacturer_paths(current_user.manufacturer_code)
        procurement_path = own_paths.shared_zone / "procurement.json"
        procurement = self.drive_service.json_service.read_json(procurement_path, {"schema_version": "1.0", "requests": []})
        request = next((item for item in procurement.get("requests", []) if item.get("request_id") == request_id), None)
        if not request or request.get("status") != "OPEN":
            raise ValueError("Procurement request is no longer OPEN.")

        inventory_path = own_paths.shared_zone / "inventory.json"
        inventory = self.drive_service.json_service.read_json(inventory_path, {"schema_version": "1.0", "items": []})
        ranked = self.procurement_matching_service.rank_suppliers(request, inventory.get("items", []))
        supplier_item = next((item for item in ranked if int(item.get("quantity", 0) - item.get("reserved_quantity", 0)) >= int(request["required_qty"])), None)
        if not supplier_item:
            raise ValueError("Insufficient supplier inventory for procurement acceptance.")

        minimum_advance = round(int(request["required_qty"]) * unit_price * 0.5, 2)
        if advance_amount < minimum_advance:
            raise ValueError("Advance must be at least 50% before procurement commit.")

        buyer_paths = self.drive_service.get_manufacturer_paths(request["requested_by"])
        agreements_path = buyer_paths.shared_zone / "agreements.json"
        pdf_path = buyer_paths.private_zone / "invoices" / f"{transaction_id}.pdf"

        try:
            self._register_target(context, inventory_path)
            self._register_target(context, procurement_path)
            self._register_target(context, agreements_path)

            def inventory_mutator(payload: dict[str, Any]) -> dict[str, Any]:
                payload.setdefault("schema_version", "1.0")
                payload.setdefault("manufacturer_code", current_user.manufacturer_code)
                payload.setdefault("items", [])
                matched = next((item for item in payload["items"] if item.get("product_code") == request["product_id"]), None)
                if not matched:
                    raise ValueError("Supplier inventory record disappeared before commit.")
                available = int(matched.get("quantity", 0) - matched.get("reserved_quantity", 0))
                if available < int(request["required_qty"]):
                    raise ValueError("Supplier inventory changed before commit.")
                matched["reserved_quantity"] = int(matched.get("reserved_quantity", 0)) + int(request["required_qty"])
                matched["last_transaction_id"] = transaction_id
                return payload

            self.safe_drive_write_service.mutate_json(inventory_path, inventory_mutator, schema_name="inventory")

            agreement = self.agreement_service.create_procurement_agreement(
                buyer_manufacturer_id=request["requested_by"],
                seller_manufacturer_id=current_user.manufacturer_code,
                product_code=request["product_id"],
                quantity=int(request["required_qty"]),
                unit_price=unit_price,
            )
            agreement["transaction_id"] = transaction_id
            agreement["advance_amount"] = minimum_advance
            agreement = self.agreement_service.confirm_advance(agreement, advance_amount)
            pdf_generated_path = self.agreement_service.generate_pdf(agreement, pdf_path)
            agreement["pdf_path"] = str(pdf_generated_path)
            context.rollback_cleanup_files.append(pdf_generated_path)

            def procurement_mutator(payload: dict[str, Any]) -> dict[str, Any]:
                payload.setdefault("schema_version", "1.0")
                payload.setdefault("requests", [])
                found = False
                for item in payload["requests"]:
                    if item.get("request_id") == request_id:
                        if item.get("status") != "OPEN":
                            raise ValueError("Procurement request changed before commit.")
                        item["status"] = "ACCEPTED"
                        item["accepted_by"] = current_user.manufacturer_code
                        item["agreement_id"] = agreement["agreement_id"]
                        item["transaction_id"] = transaction_id
                        found = True
                        break
                if not found:
                    raise ValueError("Procurement request missing during commit.")
                return payload

            self.safe_drive_write_service.mutate_json(procurement_path, procurement_mutator, schema_name="procurement")

            if not agreements_path.exists():
                self.safe_drive_write_service.replace_document(
                    agreements_path,
                    {"schema_version": "1.0", "manufacturer_code": request["requested_by"], "agreements": []},
                )

            self.safe_drive_write_service.append_record(
                agreements_path,
                "agreements",
                {"schema_version": "1.0", **agreement},
            )

            context.state = "COMMITTED"
            self._write_journal(context)

            self.audit_service.log_event(
                "procurement_transaction_committed",
                actor=current_user.email,
                details={
                    "transaction_id": transaction_id,
                    "request_id": request_id,
                    "agreement_id": agreement["agreement_id"],
                },
            )
        except Exception as exc:  # noqa: BLE001
            context.state = "ROLLED_BACK"
            context.error_message = str(exc)
            self.rollback_service.restore_files(context.backup_targets)
            for cleanup_target in context.rollback_cleanup_files:
                self.rollback_service.remove_file_if_exists(cleanup_target)
            self._write_journal(context)
            self.logging_service.log_error(
                "transaction_failures",
                "Procurement transaction rolled back",
                {"transaction_id": transaction_id, "request_id": request_id, "error": str(exc)},
            )
            raise

        try:
            self._emit_event_safe(
                "PROCUREMENT_ACCEPTED",
                {
                    "transaction_id": transaction_id,
                    "correlation_id": request_id,
                    "request_id": request_id,
                    "agreement_id": agreement["agreement_id"],
                    "accepted_by": current_user.manufacturer_code,
                },
            )
            self.gmail_service.enqueue_message(
                to_email=current_user.email,
                subject="Procurement Request Accepted",
                body=f"Transaction {transaction_id} accepted procurement request {request_id}.",
                notification_type="procurement_request_accepted",
            )
            self.gmail_service.enqueue_message(
                to_email=current_user.email,
                subject="Agreement Generated",
                body=f"Agreement {agreement['agreement_id']} created under transaction {transaction_id}.",
                notification_type="agreement_generated",
            )
        except Exception as exc:  # noqa: BLE001
            self.logging_service.log_error(
                "notification_failures",
                "Side effect failed after procurement commit",
                {"transaction_id": transaction_id, "error": str(exc)},
            )

        return {
            "transaction_id": transaction_id,
            "request_id": request_id,
            "agreement_id": agreement["agreement_id"],
            "status": context.state,
        }

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
                targets = [Path(item) for item in payload.get("backup_targets", [])]
                self.rollback_service.restore_files(targets)
                for item in payload.get("rollback_cleanup_files", []):
                    self.rollback_service.remove_file_if_exists(Path(item))
                payload["state"] = "ROLLED_BACK"
                path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                recovered.append(payload)
        return recovered
