from __future__ import annotations

from datetime import UTC, datetime

from services.auth_service import get_bootstrap_primary_admin
from services.id_service import IdService


class LedgerService:
    def __init__(self, data_service) -> None:
        self.data_service = data_service
        self.id_service = IdService()

    def _build_account_key(self, owner_email: str) -> str:
        primary_admin = get_bootstrap_primary_admin()
        return f"{primary_admin.get('email', '')}::{owner_email}"

    def _append_entry(
        self,
        *,
        order_id: str,
        product_id: str,
        source_channel: str,
        owner_email: str,
        owner_role: str,
        amount: float,
        entry_type: str,
        source: str,
        status: str = "OPEN",
        metadata: dict | None = None,
        delivery_partner_email: str = "",
    ) -> dict:
        primary_admin = get_bootstrap_primary_admin()
        record = {
            "ledger_id": self.id_service.next("ledger"),
            "account_key": self._build_account_key(owner_email),
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
            "delivery_partner_email": str(delivery_partner_email or "").strip().lower(),
            "amount": round(float(amount or 0), 2),
            "credit": round(float(amount or 0), 2),
            "debit": 0.0,
            "source": source,
            "entry_type": entry_type,
            "service_type": str((metadata or {}).get("service_type", "product")).strip().lower(),
            "status": status,
            "metadata": metadata or {},
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.data_service.get_collection_ref("ledger").append(record)
        return record

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
        return self._append_entry(
            order_id=order_id,
            product_id=product_id,
            source_channel=source_channel,
            owner_email=owner_email,
            owner_role=owner_role,
            amount=amount,
            entry_type="PAYABLE_TO_OWNER",
            source="ORDER",
            status="OPEN",
            metadata=metadata,
        )

    def create_order_runtime_entries(self, *, order: dict, trigger: str, created_by: str = "") -> list[dict]:
        if not order:
            return []
        internal = dict(order.get("internal", {}) or {})
        financials = dict(order.get("financials", {}) or {})
        owner_email = str(order.get("owner_email", "")).strip().lower()
        owner_role = str(order.get("owner_role", "")).strip().lower()
        order_id = str(order.get("order_id", "")).strip()
        product_id = str(order.get("product_id", "")).strip()
        source_channel = str(order.get("source_channel", "")).strip().lower()
        delivery_partner_email = str(order.get("preferred_delivery_partner_email", "")).strip().lower()
        entries: list[dict] = []
        entry_specs = [
            ("PAYABLE_TO_OWNER", float(internal.get("owner_payable_amount", 0) or 0), "product"),
            ("PLATFORM_MARGIN", float(internal.get("admin_margin", 0) or 0), "margin"),
            ("PACKAGING_FEE", float(financials.get("packaging_charge", 0) or 0), "packaging"),
            ("SHIPPING_FEE", float(financials.get("shipping_charge", 0) or 0), "shipping"),
        ]
        for entry_type, amount, service_type in entry_specs:
            if amount <= 0:
                continue
            entries.append(
                self._append_entry(
                    order_id=order_id,
                    product_id=product_id,
                    source_channel=source_channel,
                    owner_email=owner_email,
                    owner_role=owner_role,
                    amount=amount,
                    entry_type=entry_type,
                    source="ORDER_RUNTIME",
                    status="OPEN",
                    delivery_partner_email=delivery_partner_email,
                    metadata={
                        "trigger": trigger,
                        "created_by": created_by,
                        "service_type": service_type,
                        "market_type": str(order.get("market_type", "")).strip(),
                    },
                )
            )
        return entries

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
        account_key = self._build_account_key(owner_email)
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
                    "admin_email": admin.get("email", ""),
                    "owner_email": owner.get("email", ""),
                    "owner_role": owner.get("role", ""),
                    "total_payable": 0.0,
                    "total_paid": 0.0,
                    "balance": 0.0,
                    "platform_margin": 0.0,
                    "packaging_revenue": 0.0,
                    "shipping_revenue": 0.0,
                    "last_payment_date": "",
                    "status": "OPEN",
                },
            )
            entry_type = str(row.get("entry_type", "")).upper()
            amount = float(row.get("credit", row.get("amount", 0)) or 0)
            if entry_type == "PAYABLE_TO_OWNER":
                bucket["total_payable"] += amount
            elif entry_type == "PAYMENT_TO_OWNER":
                bucket["total_paid"] += float(row.get("debit", row.get("amount", 0)) or 0)
                bucket["last_payment_date"] = str(row.get("created_at", "") or bucket.get("last_payment_date", ""))
            elif entry_type == "PLATFORM_MARGIN":
                bucket["platform_margin"] += amount
            elif entry_type == "PACKAGING_FEE":
                bucket["packaging_revenue"] += amount
            elif entry_type == "SHIPPING_FEE":
                bucket["shipping_revenue"] += amount
        for bucket in grouped.values():
            bucket["balance"] = round(float(bucket["total_payable"]) - float(bucket["total_paid"]), 2)
            bucket["platform_margin"] = round(float(bucket["platform_margin"]), 2)
            bucket["packaging_revenue"] = round(float(bucket["packaging_revenue"]), 2)
            bucket["shipping_revenue"] = round(float(bucket["shipping_revenue"]), 2)
            if bucket["total_paid"] <= 0 and bucket["balance"] > 0:
                bucket["status"] = "OPEN"
            elif bucket["balance"] > 0:
                bucket["status"] = "PARTIALLY_PAID"
            else:
                bucket["status"] = "SETTLED"
        return list(grouped.values())

    def summarize_accounts_by_owner_role(self, *, viewer_email: str = "", role: str = "platform_admin") -> dict[str, list[dict]]:
        summaries = self.summarize_accounts(viewer_email=viewer_email, role=role)
        grouped: dict[str, list[dict]] = {
            "manufacturer": [],
            "mahajan": [],
            "other": [],
        }
        for row in summaries:
            owner_role = str(row.get("owner_role", "")).strip().lower()
            if owner_role in grouped:
                grouped[owner_role].append(row)
            else:
                grouped["other"].append(row)
        return grouped

    def summarize_admin_totals(self) -> list[dict]:
        grouped = self.summarize_accounts_by_owner_role(role="platform_admin")
        rows: list[dict] = []
        for role_name, accounts in grouped.items():
            if not accounts:
                continue
            rows.append(
                {
                    "owner_group": role_name.title(),
                    "account_count": len(accounts),
                    "total_payable": round(sum(float(row.get("total_payable", 0) or 0) for row in accounts), 2),
                    "total_paid": round(sum(float(row.get("total_paid", 0) or 0) for row in accounts), 2),
                    "balance": round(sum(float(row.get("balance", 0) or 0) for row in accounts), 2),
                    "platform_margin": round(sum(float(row.get("platform_margin", 0) or 0) for row in accounts), 2),
                    "packaging_revenue": round(sum(float(row.get("packaging_revenue", 0) or 0) for row in accounts), 2),
                    "shipping_revenue": round(sum(float(row.get("shipping_revenue", 0) or 0) for row in accounts), 2),
                    "open_accounts": len([row for row in accounts if str(row.get("status", "")).upper() == "OPEN"]),
                }
            )
        return rows
