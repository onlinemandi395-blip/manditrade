from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from constants.statuses import STATUS_CANCELLED, STATUS_DISPUTED, STATUS_OVERDUE, STATUS_PAID, STATUS_PARTIAL, STATUS_PENDING


class SettlementService:
    def __init__(
        self,
        *,
        governance_service,
        id_allocator_service,
        safe_drive_write_service,
        json_service,
        runtime_root: Path,
        event_notification_service=None,
    ) -> None:
        self.governance_service = governance_service
        self.id_allocator_service = id_allocator_service
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.runtime_root = runtime_root
        self.event_notification_service = event_notification_service
        self.exports_root = runtime_root / "exports"

    def ensure_transaction(
        self,
        *,
        transaction_type: str,
        related_order_id: str,
        payer_role: str,
        payer_id: str,
        payee_role: str,
        payee_id: str,
        gross_amount: float,
        commission_amount: float = 0,
        packaging_amount: float = 0,
        courier_amount: float = 0,
        net_amount: float | None = None,
        currency: str = "INR",
        payment_mode: str = "MANUAL",
        payment_reference: str = "",
        status: str = STATUS_PENDING,
        due_date: str = "",
        created_by: str = "system",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        existing = next(
            (
                item
                for item in self.governance_service.list_financial_transactions()
                if item.get("related_order_id") == related_order_id
                and str(item.get("transaction_type", "")).upper() == str(transaction_type).upper()
                and item.get("payer_id") == payer_id
                and item.get("payee_id") == payee_id
            ),
            None,
        )
        base = dict(existing or {})
        payments = list(base.get("payments", []))
        gross_value = round(float(gross_amount or 0), 2)
        commission_value = round(float(commission_amount or 0), 2)
        packaging_value = round(float(packaging_amount or 0), 2)
        courier_value = round(float(courier_amount or 0), 2)
        paid_amount = round(sum(float(item.get("amount", 0) or 0) for item in payments), 2)
        net_value = round(float(net_amount if net_amount is not None else gross_value), 2)
        now = datetime.now(UTC).isoformat()
        transaction = {
            "financial_transaction_id": base.get("financial_transaction_id") or self.id_allocator_service.allocate("financial_transaction"),
            "transaction_type": str(transaction_type or "").strip().upper(),
            "related_order_id": str(related_order_id or "").strip(),
            "payer_role": str(payer_role or "").strip(),
            "payer_id": str(payer_id or "").strip(),
            "payee_role": str(payee_role or "").strip(),
            "payee_id": str(payee_id or "").strip(),
            "gross_amount": gross_value,
            "commission_amount": commission_value,
            "packaging_amount": packaging_value,
            "courier_amount": courier_value,
            "net_amount": net_value,
            "currency": currency,
            "payment_mode": str(payment_mode or "").strip(),
            "payment_reference": str(payment_reference or base.get("payment_reference") or "").strip(),
            "status": self._derive_status(
                requested_status=status,
                paid_amount=paid_amount,
                gross_amount=gross_value,
                due_date=due_date or str(base.get("due_date") or ""),
            ),
            "due_date": str(due_date or base.get("due_date") or ""),
            "paid_at": base.get("paid_at", ""),
            "created_at": base.get("created_at") or now,
            "updated_at": now,
            "created_by": str(base.get("created_by") or created_by or "system"),
            "updated_by": str(created_by or "system"),
            "version": int(base.get("version", 1) or 1),
            "payments": payments,
            "paid_amount": paid_amount,
            "outstanding_balance": round(gross_value - paid_amount, 2),
            "payment_proof_url": str(base.get("payment_proof_url") or ""),
            "payment_proof_uploaded_at": str(base.get("payment_proof_uploaded_at") or ""),
            "payment_verified_by": str(base.get("payment_verified_by") or ""),
            "payment_verified_at": str(base.get("payment_verified_at") or ""),
            "metadata": {**dict(base.get("metadata", {}) or {}), **dict(metadata or {})},
        }
        return self.governance_service.upsert_financial_transaction(transaction)

    def record_payment(
        self,
        *,
        financial_transaction_id: str,
        amount: float,
        actor_id: str,
        payment_reference: str = "",
        payment_mode: str = "MANUAL",
        payment_proof_url: str = "",
        verified: bool = False,
        note: str = "",
    ) -> dict[str, Any]:
        transaction = self.governance_service.get_financial_transaction(financial_transaction_id)
        if not transaction:
            raise ValueError("Financial transaction not found.")
        payment_amount = round(float(amount or 0), 2)
        if payment_amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")
        payments = list(transaction.get("payments", []))
        payments.append(
            {
                "payment_id": self.id_allocator_service.allocate("payment"),
                "amount": payment_amount,
                "payment_reference": str(payment_reference or "").strip(),
                "payment_mode": str(payment_mode or "MANUAL").strip().upper(),
                "payment_proof_url": str(payment_proof_url or "").strip(),
                "verified": bool(verified),
                "note": str(note or "").strip(),
                "created_at": datetime.now(UTC).isoformat(),
                "created_by": actor_id,
            }
        )
        gross_amount = float(transaction.get("gross_amount", 0) or 0)
        paid_amount = round(sum(float(item.get("amount", 0) or 0) for item in payments), 2)
        status = self._derive_status(
            requested_status=str(transaction.get("status", STATUS_PENDING)),
            paid_amount=paid_amount,
            gross_amount=gross_amount,
            due_date=str(transaction.get("due_date", "")),
        )
        updates = {
            **transaction,
            "payments": payments,
            "paid_amount": paid_amount,
            "outstanding_balance": round(gross_amount - paid_amount, 2),
            "payment_reference": str(payment_reference or transaction.get("payment_reference") or "").strip(),
            "payment_mode": str(payment_mode or transaction.get("payment_mode") or "MANUAL").strip().upper(),
            "payment_proof_url": str(payment_proof_url or transaction.get("payment_proof_url") or "").strip(),
            "payment_proof_uploaded_at": datetime.now(UTC).isoformat() if payment_proof_url else str(transaction.get("payment_proof_uploaded_at") or ""),
            "payment_verified_by": actor_id if verified else str(transaction.get("payment_verified_by") or ""),
            "payment_verified_at": datetime.now(UTC).isoformat() if verified else str(transaction.get("payment_verified_at") or ""),
            "paid_at": datetime.now(UTC).isoformat() if status == STATUS_PAID else str(transaction.get("paid_at") or ""),
            "status": status,
            "updated_by": actor_id,
        }
        saved = self.governance_service.upsert_financial_transaction(updates)
        if verified and self.event_notification_service:
            self.event_notification_service.emit(
                "PAYMENT_VERIFIED",
                {
                    "entity_type": "FINANCIAL_TRANSACTION",
                    "entity_id": saved["financial_transaction_id"],
                    "title": "Payment verified",
                    "message": f"Payment verified for {saved.get('related_order_id', saved['financial_transaction_id'])}.",
                    "manufacturer_code": saved.get("payer_id", "") if saved.get("payer_role") == "manufacturer" else saved.get("payee_id", ""),
                },
            )
        return saved

    def attach_payment_proof(
        self,
        *,
        financial_transaction_id: str,
        proof_url: str,
        actor_id: str,
        payment_reference: str = "",
    ) -> dict[str, Any]:
        transaction = self.governance_service.get_financial_transaction(financial_transaction_id)
        if not transaction:
            raise ValueError("Financial transaction not found.")
        updates = {
            **transaction,
            "payment_reference": str(payment_reference or transaction.get("payment_reference") or "").strip(),
            "payment_proof_url": str(proof_url or "").strip(),
            "payment_proof_uploaded_at": datetime.now(UTC).isoformat(),
            "updated_by": actor_id,
        }
        return self.governance_service.upsert_financial_transaction(updates)

    def mark_overdue_transactions(self) -> list[dict[str, Any]]:
        updated: list[dict[str, Any]] = []
        today = datetime.now(UTC).date().isoformat()
        for transaction in self.governance_service.list_financial_transactions():
            if str(transaction.get("status", "")).upper() in {STATUS_PAID, STATUS_CANCELLED, STATUS_DISPUTED}:
                continue
            due_date = str(transaction.get("due_date") or "")
            if due_date and due_date < today:
                transaction["status"] = STATUS_OVERDUE
                transaction["updated_by"] = "automation"
                saved = self.governance_service.upsert_financial_transaction(transaction)
                updated.append(saved)
                if self.event_notification_service:
                    self.event_notification_service.emit(
                        "PAYMENT_OVERDUE",
                        {
                            "entity_type": "FINANCIAL_TRANSACTION",
                            "entity_id": saved["financial_transaction_id"],
                            "title": "Payment overdue",
                            "message": f"Payment overdue for {saved.get('related_order_id', saved['financial_transaction_id'])}.",
                            "manufacturer_code": saved.get("payer_id", "") if saved.get("payer_role") == "manufacturer" else saved.get("payee_id", ""),
                        },
                    )
        return updated

    def summarize(self, *, role: str | None = None, owner_id: str | None = None) -> dict[str, Any]:
        rows = self._filter_transactions(role=role, owner_id=owner_id)
        total_gross = round(sum(float(item.get("gross_amount", 0) or 0) for item in rows), 2)
        total_outstanding = round(sum(float(item.get("outstanding_balance", 0) or 0) for item in rows), 2)
        total_commission = round(sum(float(item.get("commission_amount", 0) or 0) for item in rows), 2)
        total_packaging = round(sum(float(item.get("packaging_amount", 0) or 0) for item in rows), 2)
        total_courier = round(sum(float(item.get("courier_amount", 0) or 0) for item in rows), 2)
        status_counts: dict[str, int] = {}
        for item in rows:
            key = str(item.get("status", STATUS_PENDING)).upper()
            status_counts[key] = status_counts.get(key, 0) + 1
        return {
            "transaction_count": len(rows),
            "gross_amount": total_gross,
            "outstanding_balance": total_outstanding,
            "commission_amount": total_commission,
            "packaging_amount": total_packaging,
            "courier_amount": total_courier,
            "status_counts": status_counts,
        }

    def list_transactions(self, *, role: str | None = None, owner_id: str | None = None) -> list[dict[str, Any]]:
        return self._filter_transactions(role=role, owner_id=owner_id)

    def export_rows(self, *, role: str | None = None, owner_id: str | None = None) -> Path:
        rows = self._filter_transactions(role=role, owner_id=owner_id)
        self.exports_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        target = self.exports_root / f"finance_summary_{stamp}.json"
        self.safe_drive_write_service.replace_document(
            target,
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "role": role or "",
                "owner_id": owner_id or "",
                "rows": rows,
            },
        )
        return target

    def _filter_transactions(self, *, role: str | None, owner_id: str | None) -> list[dict[str, Any]]:
        rows = self.governance_service.list_financial_transactions()
        if not role or not owner_id:
            return rows
        role_key = str(role or "").strip().lower()
        owner_key = str(owner_id or "").strip()
        filtered: list[dict[str, Any]] = []
        for row in rows:
            if row.get("payer_role") == role_key and row.get("payer_id") == owner_key:
                filtered.append(row)
            elif row.get("payee_role") == role_key and row.get("payee_id") == owner_key:
                filtered.append(row)
        return filtered

    def _derive_status(self, *, requested_status: str, paid_amount: float, gross_amount: float, due_date: str) -> str:
        requested = str(requested_status or "PENDING").strip().upper()
        if requested in {STATUS_CANCELLED, STATUS_DISPUTED}:
            return requested
        if paid_amount >= gross_amount and gross_amount > 0:
            return STATUS_PAID
        if paid_amount > 0:
            return STATUS_PARTIAL
        if due_date and due_date < datetime.now(UTC).date().isoformat():
            return STATUS_OVERDUE
        return requested if requested in {STATUS_PENDING, STATUS_PARTIAL, STATUS_PAID, STATUS_OVERDUE} else STATUS_PENDING
