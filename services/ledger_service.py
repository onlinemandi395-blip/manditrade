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
        entry = {
            "entry_id": self.id_allocator_service.allocate("ledger_entry"),
            "entry_type": entry_type,
            "amount": round(float(amount), 2),
            "paid_amount": round(float(paid_amount), 2),
            "balance_due": round(float(amount) - float(paid_amount), 2),
            "due_date": (datetime.now(UTC) + timedelta(days=int(ledger_days))).date().isoformat(),
            "note": note,
            "status": "PAID" if float(amount) <= float(paid_amount) else "PENDING",
            "created_at": datetime.now(UTC).isoformat(),
            "reminders_sent": [],
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
                        entry["paid_amount"] = round(float(entry.get("paid_amount", 0)) + float(amount), 2)
                        entry["balance_due"] = round(float(entry.get("amount", 0)) - float(entry["paid_amount"]), 2)
                        entry["status"] = "PAID" if entry["balance_due"] <= 0 else "PENDING"
                        entry["adjustment_note"] = note
                        updated = entry
                        return payload
            raise ValueError(f"Ledger entry not found: {entry_id}")

        self.safe_drive_write_service.mutate_json(path, mutator)
        return updated or {}
