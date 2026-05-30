from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class ProcurementContext:
    transaction_id: str
    state: str = "PENDING"
    affected_files: list[str] = field(default_factory=list)
    backup_targets: list[Path] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    error_message: str = ""


class ProcurementTransactionService:
    def __init__(
        self,
        drive_service,
        safe_drive_write_service,
        rollback_service,
        gmail_service,
        audit_service,
        logging_service,
        transactions_root: Path,
        event_dispatcher,
        id_allocator_service,
        dual_inventory_service,
        trade_confirmation_service,
        ledger_service,
        notification_center_service,
        domain_paths_service,
    ) -> None:
        self.drive_service = drive_service
        self.safe_drive_write_service = safe_drive_write_service
        self.rollback_service = rollback_service
        self.gmail_service = gmail_service
        self.audit_service = audit_service
        self.logging_service = logging_service
        self.transactions_root = transactions_root
        self.event_dispatcher = event_dispatcher
        self.id_allocator_service = id_allocator_service
        self.dual_inventory_service = dual_inventory_service
        self.trade_confirmation_service = trade_confirmation_service
        self.ledger_service = ledger_service
        self.notification_center_service = notification_center_service
        self.domain_paths = domain_paths_service

    def _validate_available_items(self, available_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in available_items:
            qty = int(item.get("qty", 0) or 0)
            unit_price = float(item.get("offered_unit_price", item.get("unit_price", 0)) or 0)
            if qty <= 0:
                raise ValueError("RFQ response quantity must be greater than zero.")
            if unit_price <= 0:
                raise ValueError("RFQ response offered unit price is required and must be greater than zero.")
            normalized.append(
                {
                    **item,
                    "qty": qty,
                    "offered_unit_price": round(unit_price, 2),
                    "total_price": round(qty * unit_price, 2),
                }
            )
        return normalized

    def _journal_path(self, transaction_id: str) -> Path:
        return self.transactions_root / f"{transaction_id}.json"

    def _write_journal(self, context: ProcurementContext) -> None:
        self.transactions_root.mkdir(parents=True, exist_ok=True)
        self._journal_path(context.transaction_id).write_text(
            json.dumps(
                {
                    "transaction_id": context.transaction_id,
                    "state": context.state,
                    "affected_files": context.affected_files,
                    "backup_targets": [str(item) for item in context.backup_targets],
                    "created_at": context.created_at,
                    "error_message": context.error_message,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _register_target(self, context: ProcurementContext, target: Path) -> None:
        if target not in context.backup_targets:
            context.backup_targets.append(target)
            context.affected_files.append(str(target))
            self.safe_drive_write_service.backup_file(target)

    def _rfq_doc(self, manufacturer_code: str) -> dict[str, Any]:
        return self.drive_service.json_service.read_json(self.domain_paths.rfq_path(manufacturer_code), {"schema_version": "2.0", "rfqs": [], "responses": []})

    def create_rfq_from_shortage(self, *, manufacturer_code: str, items: list[dict[str, Any]], trade_terms: dict[str, Any]) -> dict[str, Any]:
        path = self.domain_paths.rfq_path(manufacturer_code)
        if not path.exists():
            self.safe_drive_write_service.replace_document(path, {"schema_version": "2.0", "rfqs": [], "responses": []})
        rfq = {
            "rfq_id": self.id_allocator_service.allocate("rfq"),
            "buyer_manufacturer_id": manufacturer_code,
            "items": items,
            "trade_terms": trade_terms,
            "status": "OPEN",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.safe_drive_write_service.append_record(path, "rfqs", rfq)
        return rfq

    def list_requests(self, manufacturer_code: str) -> list[dict[str, Any]]:
        return self._rfq_doc(manufacturer_code).get("rfqs", [])

    def list_responses(self, manufacturer_code: str) -> list[dict[str, Any]]:
        return self._rfq_doc(manufacturer_code).get("responses", [])

    def respond_to_rfq(self, current_user, rfq_owner_code: str, rfq_id: str, available_items: list[dict[str, Any]], supplier_terms: dict[str, Any]) -> dict[str, Any]:
        transaction_id = self.id_allocator_service.allocate("transaction")
        context = ProcurementContext(transaction_id=transaction_id, state="RUNNING")
        self._write_journal(context)
        rfq_path = self.domain_paths.rfq_path(rfq_owner_code)
        inventory_path = self.domain_paths.private_self_inventory_path(current_user.manufacturer_code)
        try:
            normalized_items = self._validate_available_items(available_items)
            self._register_target(context, rfq_path)
            self._register_target(context, inventory_path)
            self.dual_inventory_service.reserve_mandi_inventory(current_user.manufacturer_code, [{"product_id": item["product_id"], "qty": item["qty"]} for item in normalized_items])
            response = {
                "response_id": self.id_allocator_service.allocate("response"),
                "supplier_manufacturer_id": current_user.manufacturer_code,
                "rfq_id": rfq_id,
                "available_items": normalized_items,
                "supplier_terms": supplier_terms,
                "status": "SUBMITTED",
                "created_at": datetime.now(UTC).isoformat(),
            }

            def mutator(payload: dict[str, Any]) -> dict[str, Any]:
                payload.setdefault("rfqs", [])
                payload.setdefault("responses", [])
                rfq = next((item for item in payload["rfqs"] if item.get("rfq_id") == rfq_id), None)
                if rfq is None:
                    raise ValueError(f"RFQ not found: {rfq_id}")
                if rfq.get("status") != "OPEN":
                    raise ValueError("RFQ is not open for responses.")
                rfq["status"] = "RESPONDED"
                payload["responses"].append(response)
                return payload

            self.safe_drive_write_service.mutate_json(rfq_path, mutator)
            self.notification_center_service.create_notification(
                rfq_owner_code,
                user_id=rfq_owner_code,
                notification_type="RFQ_ACCEPTED",
                priority="HIGH",
                title="RFQ Accepted",
                message="A supplier accepted your mandi RFQ.",
                source_type="RFQ",
                source_id=rfq_id,
            )
            context.state = "COMMITTED"
            self._write_journal(context)
        except Exception as exc:  # noqa: BLE001
            context.state = "ROLLED_BACK"
            context.error_message = str(exc)
            self.rollback_service.restore_files(context.backup_targets)
            self._write_journal(context)
            raise
        return response

    def accept_rfq_response(self, buyer_user, rfq_id: str, response_id: str) -> dict[str, Any]:
        transaction_id = self.id_allocator_service.allocate("transaction")
        context = ProcurementContext(transaction_id=transaction_id, state="RUNNING")
        self._write_journal(context)
        rfq_path = self.domain_paths.rfq_path(buyer_user.manufacturer_code)
        try:
            self._register_target(context, rfq_path)
            payload = self._rfq_doc(buyer_user.manufacturer_code)
            rfq = next((item for item in payload.get("rfqs", []) if item.get("rfq_id") == rfq_id), None)
            response = next((item for item in payload.get("responses", []) if item.get("response_id") == response_id), None)
            if rfq is None or response is None:
                raise ValueError("RFQ response not found.")
            total_amount = round(sum(float(item.get("total_price", 0) or 0) for item in response.get("available_items", [])), 2)
            if total_amount <= 0:
                raise ValueError("Buyer cannot accept an RFQ response without valid priced items.")
            rfq["status"] = "BUYER_CONFIRMED"
            response["status"] = "BUYER_CONFIRMED"
            self.safe_drive_write_service.replace_document(rfq_path, payload)
            confirmation = self.trade_confirmation_service.create_confirmation(
                buyer_user.manufacturer_code,
                source_type="MANDI_RFQ",
                source_id=rfq_id,
                confirmed_by=buyer_user.email,
                accepted_terms_snapshot={"rfq": rfq, "response": response},
            )
            rfq["trade_confirmation_id"] = confirmation["confirmation_id"]
            self.safe_drive_write_service.replace_document(rfq_path, payload)
            self.ledger_service.create_entry(
                buyer_user.manufacturer_code,
                party_a=buyer_user.manufacturer_code,
                party_b=response["supplier_manufacturer_id"],
                entry_type="MANDI_SUPPLY",
                amount=total_amount,
                paid_amount=0,
                ledger_days=int(response.get("supplier_terms", {}).get("ledger_days", 0)),
                note=response.get("supplier_terms", {}).get("freestyle_note", ""),
            )
            context.state = "COMMITTED"
            self._write_journal(context)
        except Exception as exc:  # noqa: BLE001
            context.state = "ROLLED_BACK"
            context.error_message = str(exc)
            self.rollback_service.restore_files(context.backup_targets)
            self._write_journal(context)
            raise
        return {"rfq_id": rfq_id, "response_id": response_id, "status": "BUYER_CONFIRMED"}

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
