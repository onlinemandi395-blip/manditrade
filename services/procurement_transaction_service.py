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
        governance_service=None,
        pricing_service=None,
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
        self.governance_service = governance_service
        self.pricing_service = pricing_service

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

    def list_supply_orders(self, *, manufacturer_code: str | None = None, mahajan_id: str | None = None) -> list[dict[str, Any]]:
        if not self.governance_service:
            return []
        orders = self.governance_service.list_supply_orders()
        if manufacturer_code:
            orders = [item for item in orders if item.get("manufacturer_id") == manufacturer_code]
        if mahajan_id:
            orders = [item for item in orders if item.get("mahajan_id") == mahajan_id]
        return orders

    def create_supply_request(
        self,
        *,
        manufacturer_code: str,
        raw_material_id: str,
        qty: float,
        unit: str,
        requested_by: str,
        notes: str = "",
    ) -> dict[str, Any]:
        if not self.governance_service:
            raise ValueError("Governance service not configured for supply requests.")
        order = {
            "mandi_order_id": self.id_allocator_service.allocate("order").replace("ORD-", "MO-"),
            "order_type": "mandi_order",
            "raw_material_id": raw_material_id,
            "manufacturer_id": manufacturer_code,
            "mahajan_id": "",
            "qty": float(qty or 0),
            "unit": unit,
            "requested_by": requested_by,
            "notes": notes,
            "status": "REQUESTED_BY_MANUFACTURER",
            "internal_status_history": [
                {"status": "REQUESTED_BY_MANUFACTURER", "at": datetime.now(UTC).isoformat(), "actor": requested_by}
            ],
        }
        return self.governance_service.upsert_supply_order(order)

    def assign_supply_to_mahajan(self, *, mandi_order_id: str, mahajan_id: str, admin_email: str) -> dict[str, Any]:
        if not self.governance_service:
            raise ValueError("Governance service not configured for supply requests.")
        order = self.governance_service.get_supply_order(mandi_order_id)
        if not order:
            raise ValueError("Supply order not found.")
        order["mahajan_id"] = mahajan_id
        order["status"] = "SENT_TO_MAHAJAN"
        order.setdefault("internal_status_history", []).append({"status": "SENT_TO_MAHAJAN", "at": datetime.now(UTC).isoformat(), "actor": admin_email})
        return self.governance_service.upsert_supply_order(order)

    def quote_supply_order(self, *, mandi_order_id: str, mahajan_id: str, mahajan_unit_price: float, mahajan_email: str, notes: str = "") -> dict[str, Any]:
        if not self.governance_service:
            raise ValueError("Governance service not configured for supply requests.")
        order = self.governance_service.get_supply_order(mandi_order_id)
        if not order:
            raise ValueError("Supply order not found.")
        if order.get("mahajan_id") and order.get("mahajan_id") != mahajan_id:
            raise PermissionError("Mahajan cannot quote another mahajan's supply order.")
        order["mahajan_id"] = mahajan_id
        order["mahajan_unit_price"] = round(float(mahajan_unit_price or 0), 2)
        order["mahajan_notes"] = notes
        order["status"] = "MAHAJAN_QUOTED"
        order.setdefault("internal_status_history", []).append({"status": "MAHAJAN_QUOTED", "at": datetime.now(UTC).isoformat(), "actor": mahajan_email})
        return self.governance_service.upsert_supply_order(order)

    def set_manufacturer_supply_price(
        self,
        *,
        mandi_order_id: str,
        manufacturer_unit_price: float,
        admin_email: str,
        mahajan_fee_percent: float | None = None,
    ) -> dict[str, Any]:
        if not self.governance_service or not self.pricing_service:
            raise ValueError("Supply pricing services are not configured.")
        order = self.governance_service.get_supply_order(mandi_order_id)
        if not order:
            raise ValueError("Supply order not found.")
        commission = self.pricing_service.calculate_supply_commission(
            mandi_order_id=mandi_order_id,
            mahajan_id=order.get("mahajan_id", ""),
            manufacturer_id=order.get("manufacturer_id", ""),
            raw_material_id=order.get("raw_material_id", ""),
            qty=float(order.get("qty", 0) or 0),
            unit=str(order.get("unit", "")),
            mahajan_unit_price=float(order.get("mahajan_unit_price", 0) or 0),
            manufacturer_unit_price=float(manufacturer_unit_price or 0),
            mahajan_fee_percent=mahajan_fee_percent,
        )
        order["manufacturer_unit_price"] = round(float(manufacturer_unit_price or 0), 2)
        order["commission_object"] = commission
        order["status"] = "ADMIN_PRICE_SET"
        order.setdefault("internal_status_history", []).append({"status": "ADMIN_PRICE_SET", "at": datetime.now(UTC).isoformat(), "actor": admin_email})
        return self.governance_service.upsert_supply_order(order)

    def confirm_supply_order(self, *, mandi_order_id: str, manufacturer_code: str, actor_email: str) -> dict[str, Any]:
        if not self.governance_service or not self.pricing_service:
            raise ValueError("Supply pricing services are not configured.")
        order = self.governance_service.get_supply_order(mandi_order_id)
        if not order:
            raise ValueError("Supply order not found.")
        if order.get("manufacturer_id") != manufacturer_code:
            raise PermissionError("Manufacturer cannot confirm another manufacturer's supply order.")
        order["status"] = "MANUFACTURER_CONFIRMED"
        order.setdefault("internal_status_history", []).append({"status": "MANUFACTURER_CONFIRMED", "at": datetime.now(UTC).isoformat(), "actor": actor_email})
        commission = dict(order.get("commission_object") or {})
        if not commission:
            commission = self.pricing_service.calculate_supply_commission(
                mandi_order_id=mandi_order_id,
                mahajan_id=order.get("mahajan_id", ""),
                manufacturer_id=order.get("manufacturer_id", ""),
                raw_material_id=order.get("raw_material_id", ""),
                qty=float(order.get("qty", 0) or 0),
                unit=str(order.get("unit", "")),
                mahajan_unit_price=float(order.get("mahajan_unit_price", 0) or 0),
                manufacturer_unit_price=float(order.get("manufacturer_unit_price", 0) or 0),
            )
            order["commission_object"] = commission
        self.ledger_service.create_entry(
            manufacturer_code,
            party_a="PLATFORM_ADMIN",
            party_b=manufacturer_code,
            entry_type="MANDI_LEDGER",
            amount=float(commission.get("manufacturer_bill_amount", 0) or 0),
            paid_amount=0,
            ledger_days=7,
            note=f"Admin-managed mandi supply order {mandi_order_id}",
            metadata={"ledger_scope": "mandi_ledger", "supply_order": mandi_order_id, "commission_object": commission},
        )
        self.governance_service.create_supply_ledger_entry(
            {
                "entry_id": self.id_allocator_service.allocate("ledger_entry"),
                "mandi_order_id": mandi_order_id,
                "mahajan_id": order.get("mahajan_id", ""),
                "manufacturer_id": manufacturer_code,
                "entry_type": "SUPPLY_LEDGER",
                "amount_due_to_mahajan": round(float(commission.get("mahajan_bill_amount", 0) or 0) - float(commission.get("mahajan_transaction_fee", 0) or 0), 2),
                "mahajan_transaction_fee": float(commission.get("mahajan_transaction_fee", 0) or 0),
                "status": "PENDING",
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        return self.governance_service.upsert_supply_order(order)

    def dispatch_supply_order(self, *, mandi_order_id: str, mahajan_id: str, actor_email: str) -> dict[str, Any]:
        if not self.governance_service:
            raise ValueError("Governance service not configured for supply requests.")
        order = self.governance_service.get_supply_order(mandi_order_id)
        if not order:
            raise ValueError("Supply order not found.")
        if order.get("mahajan_id") != mahajan_id:
            raise PermissionError("Mahajan cannot dispatch another mahajan's order.")
        order["status"] = "MAHAJAN_DISPATCHED"
        order.setdefault("internal_status_history", []).append({"status": "MAHAJAN_DISPATCHED", "at": datetime.now(UTC).isoformat(), "actor": actor_email})
        return self.governance_service.upsert_supply_order(order)

    def receive_supply_order(self, *, mandi_order_id: str, manufacturer_code: str, actor_email: str) -> dict[str, Any]:
        if not self.governance_service:
            raise ValueError("Governance service not configured for supply requests.")
        order = self.governance_service.get_supply_order(mandi_order_id)
        if not order:
            raise ValueError("Supply order not found.")
        if order.get("manufacturer_id") != manufacturer_code:
            raise PermissionError("Manufacturer cannot receive another manufacturer's supply order.")
        order["status"] = "MANUFACTURER_RECEIVED"
        order.setdefault("internal_status_history", []).append({"status": "MANUFACTURER_RECEIVED", "at": datetime.now(UTC).isoformat(), "actor": actor_email})
        return self.governance_service.upsert_supply_order(order)

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
