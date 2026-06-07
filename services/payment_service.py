from __future__ import annotations

from datetime import UTC, datetime
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
        return self.id_service.next_drive_id(self.data_service.admin_drive_service, "payment_reference", "MTORD")

    def build_upi_link(self, *, amount: float, reference: str) -> str:
        config = self.get_payment_config()
        if not config.get("enabled", False):
            raise ValueError("UPI payment is disabled in payment_config.json.")
        upi_id = quote(config["upi_id"])
        payee_name = quote(config["payee_name"])
        note = quote(reference)
        currency = quote(config.get("currency", "INR"))
        return f"upi://pay?pa={upi_id}&pn={payee_name}&am={float(amount or 0):.2f}&cu={currency}&tn={note}"

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

    def ensure_payment_link_fields(self, payment_record: dict) -> dict:
        record = dict(payment_record or {})
        reference = str(record.get("payment_reference", "")).strip()
        amount = float(record.get("amount_payable", record.get("amount_due", 0)) or 0)
        if not reference:
            return record
        upi_link = str(record.get("upi_link", "")).strip()
        if not upi_link:
            upi_link = self.build_upi_link(amount=amount, reference=reference)
            payment_record["upi_link"] = upi_link
        qr_payload = str(record.get("qr_payload", "")).strip()
        if not qr_payload:
            payment_record["qr_payload"] = upi_link
        return payment_record
