from __future__ import annotations

from datetime import UTC, datetime
import secrets
import string
from urllib.parse import quote

from services.id_service import IdService


class PaymentService:
    def __init__(self, data_service, cache_service) -> None:
        self.data_service = data_service
        self.cache_service = cache_service
        self.id_service = IdService()

    def get_payment_config(self) -> dict:
        config = dict(self.cache_service.get_config("payment_config") or {})
        payment = dict(config.get("payment", {}) or {})
        source = payment or config
        return {
            "upi_id": str(source.get("upi_id", "manditrade@upi")).strip(),
            "payee_name": str(source.get("payee_name", "MandiTrade")).strip(),
            "currency": str(source.get("currency", "INR")).strip() or "INR",
            "enabled": bool(source.get("enabled", True)),
        }

    def generate_payment_reference(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        existing_references = {
            str(row.get("payment_reference", "")).strip().upper()
            for row in self.data_service.get_collection_ref("payments")
            if str(row.get("payment_reference", "")).strip()
        }
        for _ in range(20):
            reference = "".join(secrets.choice(alphabet) for _ in range(10))
            if reference not in existing_references:
                return reference
        fallback_counter = self.id_service.next_drive_id(self.data_service.admin_drive_service, "payment_reference", "PAY")
        return fallback_counter.replace("-", "")[-10:].upper()

    @staticmethod
    def _encode_upi_value(value: str) -> str:
        return quote(str(value or "").strip(), safe="@._-")

    @classmethod
    def build_upi_link_from_values(
        cls,
        *,
        upi_id: str,
        payee_name: str,
        amount: float,
        currency: str,
        reference: str,
    ) -> str:
        normalized_reference = str(reference or "").strip().upper()
        note = f"MandiTrade {normalized_reference}".strip()
        query_parts = [
            ("pa", str(upi_id or "").strip()),
            ("pn", str(payee_name or "MandiTrade").strip()),
            ("am", f"{float(amount or 0):.2f}"),
            ("cu", str(currency or "INR").strip() or "INR"),
            ("tr", normalized_reference),
            ("tid", normalized_reference),
            ("tn", note),
        ]
        query = "&".join(f"{key}={cls._encode_upi_value(value)}" for key, value in query_parts if str(value).strip())
        return f"upi://pay?{query}"

    def build_upi_link(self, *, amount: float, reference: str) -> str:
        config = self.get_payment_config()
        if not config.get("enabled", False):
            raise ValueError("UPI payment is disabled in payment_config.json.")
        return self.build_upi_link_from_values(
            upi_id=str(config["upi_id"]).strip(),
            payee_name=str(config["payee_name"]).strip(),
            amount=amount,
            currency=str(config.get("currency", "INR")).strip() or "INR",
            reference=str(reference or "").strip(),
        )

    def create_payment_record(
        self,
        *,
        order_id: str,
        payer_email: str,
        amount: float,
        payment_type: str,
        created_by: str,
    ) -> dict:
        reference = self.generate_payment_reference()
        upi_link = self.build_upi_link(amount=amount, reference=reference)
        record = {
            "payment_id": self.id_service.next("payment"),
            "order_id": order_id,
            "payment_type": payment_type,
            "payer_email": str(payer_email or "").strip().lower(),
            "amount_payable": round(float(amount or 0), 2),
            "amount_due": round(float(amount or 0), 2),
            "amount_received": 0.0,
            "payment_reference": reference,
            "upi_link": upi_link,
            "qr_payload": upi_link,
            "payment_status": "PENDING",
            "status": "PAYMENT_PENDING",
            "transaction_reference": "",
            "verified_by": "",
            "verified_at": "",
            "notes": "",
            "created_at": datetime.now(UTC).isoformat(),
            "created_by": str(created_by or "").strip().lower(),
        }
        self.data_service.get_collection_ref("payments").append(record)
        return record

    def ensure_payment_link_fields(self, payment_record: dict) -> bool:
        record = dict(payment_record or {})
        reference = str(record.get("payment_reference", "")).strip()
        if not reference:
            return False
        amount = float(record.get("amount_payable", record.get("amount_due", 0)) or 0)
        upi_link = self.build_upi_link(amount=amount, reference=reference)
        changed = False
        if str(payment_record.get("upi_link", "") or "").strip() != upi_link:
            payment_record["upi_link"] = upi_link
            changed = True
        if str(payment_record.get("qr_payload", "") or "").strip() != upi_link:
            payment_record["qr_payload"] = upi_link
            changed = True
        config = self.get_payment_config()
        receiver_fields = {
            "receiver_upi_id": str(config.get("upi_id", "")).strip(),
            "receiver_payee_name": str(config.get("payee_name", "")).strip(),
            "receiver_currency": str(config.get("currency", "INR")).strip() or "INR",
            "payment_enabled": bool(config.get("enabled", False)),
        }
        for key, value in receiver_fields.items():
            if payment_record.get(key) != value:
                payment_record[key] = value
                changed = True
        return changed
