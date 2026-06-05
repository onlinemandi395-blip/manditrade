from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from services.file_lock_service import FileLockService


class IdAllocatorService:
    PREFIXES = {
        "transaction": "TXN",
        "order": "ORD",
        "agreement": "AGR",
        "dispatch": "DSP",
        "procurement": "REQ",
        "event": "EVT",
        "client": "CLIENT",
        "manufacturer": "MANU",
        "comment": "COM",
        "product": "PRD",
        "rfq": "RFQ",
        "response": "RESP",
        "confirmation": "TC",
        "ledger_entry": "LEDENT",
        "notification": "NOTIF",
        "job": "JOB",
        "worker": "WRK",
        "application": "APP",
        "public_buyer": "PB",
        "cart": "CART",
        "favorite": "FAV",
        "public_order": "PUBORD",
        "public_payment": "PUBPAY",
        "payment": "PAY",
        "alert": "ALERT",
        "invoice": "INV",
        "dispute": "DSPT",
        "financial_transaction": "FTX",
        "task": "TASK",
        "warehouse": "WH",
        "shipment": "SHP",
    }

    def __init__(self, counters_path: Path, file_lock_service: FileLockService) -> None:
        self.counters_path = counters_path
        self.file_lock_service = file_lock_service

    def allocate(self, domain: str) -> str:
        prefix = self.PREFIXES.get(domain)
        if not prefix:
            raise ValueError(f"Unsupported ID domain: {domain}")

        year = datetime.now(UTC).year
        lock_path = self.file_lock_service.acquire(self.counters_path, owner="IdAllocatorService")
        try:
            self.counters_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"schema_version": "1.0", "counters": {}}
            if self.counters_path.exists():
                try:
                    payload = json.loads(self.counters_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    payload = {"schema_version": "1.0", "counters": {}}
            counters = payload.setdefault("counters", {})
            key = f"{prefix}-{year}"
            counters[key] = int(counters.get(key, 0)) + 1
            self.counters_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return f"{prefix}-{year}-{counters[key]:06d}"
        finally:
            self.file_lock_service.release(lock_path)
