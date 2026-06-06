from __future__ import annotations

from datetime import UTC, datetime

from services.auth_service import get_bootstrap_primary_admin
from services.id_service import IdService


class LedgerService:
    def __init__(self, data_service) -> None:
        self.data_service = data_service
        self.id_service = IdService()

    def create_order_receivable(
        self,
        *,
        order_id: str,
        source_channel: str,
        owner_email: str,
        owner_role: str,
        amount: float,
        product_id: str = "",
        metadata: dict | None = None,
    ) -> dict:
        primary_admin = get_bootstrap_primary_admin()
        account_key = f"{primary_admin.get('email', '')}::{owner_email}"
        record = {
            "ledger_id": self.id_service.next("ledger"),
            "account_key": account_key,
            "order_id": order_id,
            "product_id": product_id,
            "source_channel": source_channel,
            "party_admin": {
                "email": primary_admin.get("email", ""),
                "role": "platform_admin",
            },
            "party_owner": {
                "email": owner_email,
                "role": owner_role,
            },
            "amount": float(amount or 0),
            "credit": float(amount or 0),
            "debit": 0.0,
            "source": "ORDER",
            "entry_type": "PAYABLE_TO_OWNER",
            "status": "OPEN",
            "metadata": metadata or {},
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.data_service.get_collection_ref("ledger").append(record)
        return record

    def create_payment_entry(
        self,
        *,
        owner_email: str,
        owner_role: str,
        amount: float,
        payment_mode: str,
        payment_reference: str,
        notes: str,
        created_by: str,
    ) -> dict:
        primary_admin = get_bootstrap_primary_admin()
        account_key = f"{primary_admin.get('email', '')}::{owner_email}"
        record = {
            "ledger_id": self.id_service.next("ledger"),
            "payment_id": self.id_service.next("payment"),
            "account_key": account_key,
            "party_admin": {
                "email": primary_admin.get("email", ""),
                "role": "platform_admin",
            },
            "party_owner": {
                "email": owner_email,
                "role": owner_role,
            },
            "source": "PAYMENT",
            "entry_type": "PAYMENT_TO_OWNER",
            "amount": float(amount or 0),
            "debit": float(amount or 0),
            "credit": 0.0,
            "status": "PAID",
            "payment_mode": payment_mode,
            "payment_reference": payment_reference,
            "notes": notes,
            "created_at": datetime.now(UTC).isoformat(),
            "created_by": created_by,
        }
        self.data_service.get_collection_ref("ledger").append(record)
        return record

    def summarize_accounts(self, *, viewer_email: str = "", role: str = "platform_admin") -> list[dict]:
        rows = self.data_service.get_collection_ref("ledger")
        viewer_email = str(viewer_email).strip().lower()
        grouped: dict[str, dict] = {}
        for row in rows:
            owner = dict(row.get("party_owner", {}) or row.get("party_b", {}) or {})
            admin = dict(row.get("party_admin", {}) or row.get("party_a", {}) or {})
            account_key = str(row.get("account_key", f"{admin.get('email', '')}::{owner.get('email', '')}") or "")
            if role != "platform_admin" and str(owner.get("email", "")).strip().lower() != viewer_email:
                continue
            bucket = grouped.setdefault(
                account_key,
                {
                    "account_key": account_key,
                    "owner_email": owner.get("email", ""),
                    "owner_role": owner.get("role", ""),
                    "total_payable": 0.0,
                    "total_paid": 0.0,
                    "balance": 0.0,
                    "last_payment_date": "",
                    "status": "OPEN",
                },
            )
            bucket["total_payable"] += float(row.get("credit", row.get("amount", 0)) if str(row.get("entry_type", "")).upper() == "PAYABLE_TO_OWNER" else 0)
            bucket["total_paid"] += float(row.get("debit", row.get("amount", 0)) if str(row.get("entry_type", "")).upper() == "PAYMENT_TO_OWNER" else 0)
            if str(row.get("entry_type", "")).upper() == "PAYMENT_TO_OWNER":
                bucket["last_payment_date"] = str(row.get("created_at", "") or bucket.get("last_payment_date", ""))
        for bucket in grouped.values():
            bucket["balance"] = round(float(bucket["total_payable"]) - float(bucket["total_paid"]), 2)
            bucket["status"] = "OPEN" if bucket["balance"] > 0 else "SETTLED"
        return list(grouped.values())
