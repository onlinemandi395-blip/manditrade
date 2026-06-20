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

    def get_receiver_config_for_owner(
        self,
        *,
        owner_email: str,
        owner_role: str = "",
        owner_business_details: dict | None = None,
    ) -> dict:
        fallback = self.get_payment_config()
        normalized_email = str(owner_email or "").strip().lower()
        business_details = dict(owner_business_details or {})
        product_upi_id = str(business_details.get("upi_id", "")).strip()
        product_payee_name = str(
            business_details.get("business_name", "") or business_details.get("invoice_name", "") or normalized_email.split("@")[0]
        ).strip()
        product_gst_number = str(business_details.get("gst_number", "")).strip()
        product_profile_completed = bool(business_details.get("profile_completed", False))
        if product_upi_id:
            return {
                "upi_id": product_upi_id,
                "payee_name": product_payee_name or fallback.get("payee_name", "MandiTrade"),
                "currency": str(fallback.get("currency", "INR")).strip() or "INR",
                "enabled": True,
                "owner_email": normalized_email,
                "owner_role": str(owner_role or "").strip().lower(),
                "gst_number": product_gst_number,
                "profile_completed": product_profile_completed,
                "source": "product_owner_business_details",
            }
        if not normalized_email:
            return fallback
        try:
            from services.user_profile_service import UserProfileService

            profile = UserProfileService(self.data_service).get_profile(normalized_email)
        except Exception:
            profile = {}
        details = dict(profile.get("details", {}) or {})
        upi_id = str(details.get("upi_id", "")).strip()
        payee_name = str(
            details.get("business_name", "") or profile.get("display_name", "") or normalized_email.split("@")[0]
        ).strip()
        gst_number = str(details.get("gst_number", "")).strip()
        profile_completed = bool(details.get("profile_completed", False))
        if not upi_id:
            return {
                **fallback,
                "owner_email": normalized_email,
                "owner_role": str(owner_role or "").strip().lower(),
                "gst_number": gst_number,
                "profile_completed": profile_completed,
                "source": "platform_fallback",
            }
        return {
            "upi_id": upi_id,
            "payee_name": payee_name or fallback.get("payee_name", "MandiTrade"),
            "currency": str(fallback.get("currency", "INR")).strip() or "INR",
            "enabled": True,
            "owner_email": normalized_email,
            "owner_role": str(owner_role or "").strip().lower(),
            "gst_number": gst_number,
            "profile_completed": profile_completed,
            "source": "owner_profile",
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

    @staticmethod
    def normalize_search_token(value: str) -> str:
        return "".join(ch for ch in str(value or "").strip().upper() if ch.isalnum())

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
        note = f"Payment Ref {normalized_reference}".strip()
        query_parts = [
            ("pa", str(upi_id or "").strip()),
            ("pn", str(payee_name or "MandiTrade").strip()),
            ("am", f"{float(amount or 0):.2f}"),
            ("cu", str(currency or "INR").strip() or "INR"),
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
        owner_email: str = "",
        owner_role: str = "",
        owner_business_details: dict | None = None,
    ) -> dict:
        reference = self.generate_payment_reference()
        receiver_config = self.get_receiver_config_for_owner(
            owner_email=owner_email,
            owner_role=owner_role,
            owner_business_details=owner_business_details,
        )
        if not receiver_config.get("enabled", False):
            raise ValueError("UPI payment is disabled.")
        upi_link = self.build_upi_link_from_values(
            upi_id=str(receiver_config.get("upi_id", "")).strip(),
            payee_name=str(receiver_config.get("payee_name", "MandiTrade")).strip(),
            amount=amount,
            currency=str(receiver_config.get("currency", "INR")).strip() or "INR",
            reference=reference,
        )
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
            "receiver_upi_id": str(receiver_config.get("upi_id", "")).strip(),
            "receiver_payee_name": str(receiver_config.get("payee_name", "")).strip(),
            "receiver_currency": str(receiver_config.get("currency", "INR")).strip() or "INR",
            "receiver_gst_number": str(receiver_config.get("gst_number", "")).strip(),
            "receiver_owner_email": str(receiver_config.get("owner_email", "")).strip().lower(),
            "receiver_owner_role": str(receiver_config.get("owner_role", "")).strip().lower(),
            "receiver_profile_completed": bool(receiver_config.get("profile_completed", False)),
            "receiver_source": str(receiver_config.get("source", "")).strip(),
        }
        self.data_service.get_collection_ref("payments").append(record)
        return record

    def ensure_payment_link_fields(self, payment_record: dict) -> bool:
        record = dict(payment_record or {})
        reference = str(record.get("payment_reference", "")).strip()
        if not reference:
            return False
        amount = float(record.get("amount_payable", record.get("amount_due", 0)) or 0)
        receiver_owner_email = str(record.get("receiver_owner_email", "")).strip().lower()
        receiver_owner_role = str(record.get("receiver_owner_role", "")).strip().lower()
        existing_upi_id = str(record.get("receiver_upi_id", "")).strip()
        existing_payee_name = str(record.get("receiver_payee_name", "")).strip()
        existing_gst_number = str(record.get("receiver_gst_number", "")).strip()
        receiver_source = str(record.get("receiver_source", "")).strip()
        receiver_config = self.get_receiver_config_for_owner(
            owner_email=receiver_owner_email,
            owner_role=receiver_owner_role,
        )
        if receiver_source == "product_owner_business_details" and existing_upi_id:
            receiver_config = {
                "upi_id": existing_upi_id,
                "payee_name": existing_payee_name or receiver_config.get("payee_name", "MandiTrade"),
                "currency": str(record.get("receiver_currency", receiver_config.get("currency", "INR"))).strip() or "INR",
                "enabled": True,
                "owner_email": receiver_owner_email,
                "owner_role": receiver_owner_role,
                "gst_number": existing_gst_number,
                "profile_completed": bool(record.get("receiver_profile_completed", False)),
                "source": "product_owner_business_details",
            }
        elif existing_upi_id and str(receiver_config.get("source", "")).strip() == "platform_fallback":
            receiver_config = {
                "upi_id": existing_upi_id,
                "payee_name": existing_payee_name or "Merchant",
                "currency": str(record.get("receiver_currency", "INR")).strip() or "INR",
                "enabled": True,
                "owner_email": receiver_owner_email,
                "owner_role": receiver_owner_role,
                "gst_number": existing_gst_number,
                "profile_completed": bool(record.get("receiver_profile_completed", False)),
                "source": receiver_source or "payment_record",
            }
        elif not str(receiver_config.get("upi_id", "")).strip() and existing_upi_id:
            receiver_config = {
                "upi_id": existing_upi_id,
                "payee_name": existing_payee_name or "MandiTrade",
                "currency": str(record.get("receiver_currency", "INR")).strip() or "INR",
                "enabled": True,
                "owner_email": receiver_owner_email,
                "owner_role": receiver_owner_role,
                "gst_number": existing_gst_number,
                "profile_completed": bool(record.get("receiver_profile_completed", False)),
                "source": receiver_source or "payment_record",
            }
        upi_link = self.build_upi_link_from_values(
            upi_id=str(receiver_config.get("upi_id", "")).strip(),
            payee_name=str(receiver_config.get("payee_name", "MandiTrade")).strip(),
            amount=amount,
            currency=str(receiver_config.get("currency", "INR")).strip() or "INR",
            reference=reference,
        )
        changed = False
        if str(payment_record.get("upi_link", "") or "").strip() != upi_link:
            payment_record["upi_link"] = upi_link
            changed = True
        if str(payment_record.get("qr_payload", "") or "").strip() != upi_link:
            payment_record["qr_payload"] = upi_link
            changed = True
        receiver_fields = {
            "receiver_upi_id": str(receiver_config.get("upi_id", "")).strip(),
            "receiver_payee_name": str(receiver_config.get("payee_name", "")).strip(),
            "receiver_currency": str(receiver_config.get("currency", "INR")).strip() or "INR",
            "receiver_gst_number": str(receiver_config.get("gst_number", "")).strip(),
            "receiver_owner_email": str(receiver_config.get("owner_email", "")).strip().lower(),
            "receiver_owner_role": str(receiver_config.get("owner_role", "")).strip().lower(),
            "receiver_profile_completed": bool(receiver_config.get("profile_completed", False)),
            "receiver_source": str(receiver_config.get("source", "")).strip(),
            "payment_enabled": bool(receiver_config.get("enabled", False)),
        }
        for key, value in receiver_fields.items():
            if payment_record.get(key) != value:
                payment_record[key] = value
                changed = True
        return changed

    def find_payments_by_reference(self, search_text: str, *, pending_only: bool = False) -> list[dict]:
        normalized_search = self.normalize_search_token(search_text)
        if not normalized_search:
            return []
        rows = self.data_service.get_collection_ref("payments")
        matches: list[dict] = []
        for row in rows:
            if pending_only:
                status = str(row.get("payment_status", row.get("status", ""))).strip().upper()
                if status not in {"PENDING", "PAYMENT_PENDING"}:
                    continue
            candidates = [
                row.get("payment_reference", ""),
                row.get("payment_id", ""),
                row.get("order_id", ""),
                row.get("transaction_reference", ""),
                row.get("upi_link", ""),
                row.get("qr_payload", ""),
            ]
            normalized_candidates = [self.normalize_search_token(candidate) for candidate in candidates if str(candidate or "").strip()]
            if any(normalized_search in candidate for candidate in normalized_candidates):
                matches.append(row)
        return matches
