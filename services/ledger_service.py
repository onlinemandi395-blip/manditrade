from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any


class LedgerService:
    def __init__(self, safe_drive_write_service, json_service, id_allocator_service, domain_paths_service) -> None:
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.id_allocator_service = id_allocator_service
        self.domain_paths = domain_paths_service

    def list_ledgers(self, manufacturer_code: str) -> list[dict[str, Any]]:
        path = self.domain_paths.ledger_path(manufacturer_code)
        return self.json_service.read_json(path, {"schema_version": "2.0", "ledgers": []}).get("ledgers", [])

    def _derive_entry_status(self, *, amount: float, paid_amount: float, due_date: str, dispute: bool = False) -> str:
        balance_due = round(float(amount) - float(paid_amount), 2)
        if dispute:
            return "DISPUTED"
        if balance_due <= 0:
            return "PAID"
        if float(paid_amount) > 0:
            return "PARTIAL"
        if due_date and due_date < datetime.now(UTC).date().isoformat():
            return "OVERDUE"
        return "PENDING"

    def list_ledger_entries(self, manufacturer_code: str) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for ledger in self.list_ledgers(manufacturer_code):
            for entry in ledger.get("entries", []):
                entries.append({"ledger_id": ledger.get("ledger_id"), **entry})
        return entries

    def create_entry(
        self,
        manufacturer_code: str,
        *,
        party_a: str,
        party_b: str,
        entry_type: str,
        amount: float,
        paid_amount: float,
        ledger_days: int,
        note: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        path = self.domain_paths.ledger_path(manufacturer_code)
        if not path.exists():
            self.safe_drive_write_service.replace_document(path, {"schema_version": "2.0", "ledgers": []})
        ledger_id = f"LEDGER-{party_a}-{party_b}"
        due_date = (datetime.now(UTC) + timedelta(days=int(ledger_days))).date().isoformat()
        amount_value = round(float(amount), 2)
        paid_amount_value = round(float(paid_amount), 2)
        entry = {
            "entry_id": self.id_allocator_service.allocate("ledger_entry"),
            "entry_type": entry_type,
            "amount": amount_value,
            "paid_amount": paid_amount_value,
            "balance_due": round(amount_value - paid_amount_value, 2),
            "due_date": due_date,
            "note": note,
            "status": self._derive_entry_status(amount=amount_value, paid_amount=paid_amount_value, due_date=due_date),
            "created_at": datetime.now(UTC).isoformat(),
            "reminders_sent": [],
            "payments": [],
            "metadata": metadata or {},
        }

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload.setdefault("schema_version", "2.0")
            payload.setdefault("ledgers", [])
            ledger = next((item for item in payload["ledgers"] if item.get("ledger_id") == ledger_id), None)
            if ledger is None:
                ledger = {"ledger_id": ledger_id, "party_a": party_a, "party_b": party_b, "entries": []}
                payload["ledgers"].append(ledger)
            ledger["entries"].append(entry)
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator)
        return entry

    def list_ledgers_for_role(self, manufacturer_code: str, role: str) -> list[dict[str, Any]]:
        ledgers = self.list_ledgers(manufacturer_code)
        if role != "client":
            return ledgers
        sanitized: list[dict[str, Any]] = []
        for ledger in ledgers:
            sanitized_entries = []
            for entry in ledger.get("entries", []):
                clean = dict(entry)
                metadata = dict(clean.get("metadata", {}) or {})
                metadata.pop("commission_breakdown", None)
                metadata.pop("gross_profit", None)
                metadata.pop("mandi_price", None)
                clean["metadata"] = metadata
                sanitized_entries.append(clean)
            sanitized.append({**ledger, "entries": sanitized_entries})
        return sanitized

    def add_payment(self, manufacturer_code: str, ledger_id: str, entry_id: str, amount: float, note: str = "") -> dict[str, Any]:
        path = self.domain_paths.ledger_path(manufacturer_code)
        updated: dict[str, Any] | None = None

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            nonlocal updated
            for ledger in payload.get("ledgers", []):
                if ledger.get("ledger_id") != ledger_id:
                    continue
                for entry in ledger.get("entries", []):
                    if entry.get("entry_id") == entry_id:
                        payment_amount = round(float(amount), 2)
                        if payment_amount <= 0:
                            raise ValueError("Payment amount must be greater than zero.")
                        payment_record = {
                            "payment_id": self.id_allocator_service.allocate("payment"),
                            "ledger_id": ledger_id,
                            "entry_id": entry_id,
                            "order_id": entry.get("metadata", {}).get("order_id") or entry.get("metadata", {}).get("supply_order") or "",
                            "amount_due": round(float(entry.get("amount", 0) or 0), 2),
                            "amount_paid": payment_amount,
                            "remaining_due": 0.0,
                            "payment_mode": "OTHER",
                            "payment_reference": "",
                            "payment_note": note,
                            "paid_at": datetime.now(UTC).isoformat(),
                            "verified_by": "",
                            "status": "PARTIAL",
                        }
                        entry.setdefault("payments", []).append(payment_record)
                        entry["paid_amount"] = round(float(entry.get("paid_amount", 0)) + payment_amount, 2)
                        entry["balance_due"] = round(float(entry.get("amount", 0)) - float(entry["paid_amount"]), 2)
                        payment_record["remaining_due"] = entry["balance_due"]
                        payment_record["status"] = "PAID" if entry["balance_due"] <= 0 else "PARTIAL"
                        entry["status"] = self._derive_entry_status(
                            amount=float(entry.get("amount", 0) or 0),
                            paid_amount=float(entry["paid_amount"]),
                            due_date=str(entry.get("due_date", "")),
                            dispute=str(entry.get("status", "")).upper() == "DISPUTED",
                        )
                        entry["adjustment_note"] = note
                        updated = entry
                        return payload
            raise ValueError(f"Ledger entry not found: {entry_id}")

        self.safe_drive_write_service.mutate_json(path, mutator)
        return updated or {}

    def summarize_ledgers(self, manufacturer_code: str) -> dict[str, Any]:
        ledgers = self.list_ledgers(manufacturer_code)
        total_entries = 0
        pending_entries = 0
        partial_entries = 0
        total_amount = 0.0
        total_balance_due = 0.0
        for ledger in ledgers:
            for entry in ledger.get("entries", []):
                total_entries += 1
                total_amount += float(entry.get("amount", 0) or 0)
                total_balance_due += float(entry.get("balance_due", 0) or 0)
                status = str(entry.get("status") or "").upper()
                if status in {"PENDING", "OVERDUE"}:
                    pending_entries += 1
                if status == "PARTIAL":
                    partial_entries += 1
        return {
            "manufacturer_code": manufacturer_code,
            "ledger_groups": len(ledgers),
            "total_entries": total_entries,
            "pending_entries": pending_entries,
            "partial_entries": partial_entries,
            "total_amount": round(total_amount, 2),
            "total_balance_due": round(total_balance_due, 2),
        }
