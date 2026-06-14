from __future__ import annotations

from datetime import UTC, datetime, timedelta
import random

from services.gmail_delivery_service import GmailDeliveryService
from services.gmail_queue_service import GmailQueueService


class ProductConsentService:
    CONFIG_PATH = "00_config/product_owner_consent.json"
    RUNTIME_PATH = "14_runtime/product_owner_consents.json"

    def __init__(self, data_service, cache_service) -> None:
        self.data_service = data_service
        self.cache_service = cache_service
        self.admin_drive_service = data_service.admin_drive_service
        self.gmail_queue_service = GmailQueueService(data_service)
        self.gmail_delivery_service = GmailDeliveryService(data_service)

    def get_config(self) -> dict:
        config = dict(self.cache_service.get_config("product_owner_consent") or {})
        consent = dict(config.get("product_owner_consent", config) or {})
        return {
            "enabled": bool(consent.get("enabled", True)),
            "otp_length": int(consent.get("otp_length", 6) or 6),
            "otp_expiry_minutes": int(consent.get("otp_expiry_minutes", 15) or 15),
            "agreement_title": str(consent.get("agreement_title", "Product Onboarding Consent Agreement")).strip(),
            "agreement_body": str(consent.get("agreement_body", "")).strip(),
            "email_subject": str(consent.get("email_subject", "Consent OTP for product onboarding")).strip(),
            "email_body_template": str(consent.get("email_body_template", "")).strip(),
        }

    def _read_runtime(self) -> dict:
        try:
            return dict(self.admin_drive_service.read_json(self.RUNTIME_PATH) or {})
        except FileNotFoundError:
            return {"schema_version": 1, "consents": []}

    def _write_runtime(self, payload: dict) -> None:
        self.admin_drive_service.write_json(self.RUNTIME_PATH, payload)

    def _build_consent_key(self, *, owner_email: str, product_name: str, requested_by: str) -> str:
        return "||".join(
            [
                str(owner_email or "").strip().lower(),
                str(product_name or "").strip().lower(),
                str(requested_by or "").strip().lower(),
            ]
        )

    def _render_agreement(self, *, product_name: str, owner_email: str, requested_by: str) -> str:
        config = self.get_config()
        template = config["agreement_body"]
        replacements = {
            "{product_name}": str(product_name or "").strip(),
            "{owner_email}": str(owner_email or "").strip().lower(),
            "{requested_by}": str(requested_by or "").strip().lower(),
            "{agreement_title}": config["agreement_title"],
        }
        rendered = template
        for key, value in replacements.items():
            rendered = rendered.replace(key, value)
        return rendered

    def _render_email_body(self, *, product_name: str, owner_email: str, requested_by: str, otp_code: str) -> str:
        config = self.get_config()
        template = config["email_body_template"]
        replacements = {
            "{product_name}": str(product_name or "").strip(),
            "{owner_email}": str(owner_email or "").strip().lower(),
            "{requested_by}": str(requested_by or "").strip().lower(),
            "{otp_code}": otp_code,
            "{agreement_title}": config["agreement_title"],
            "{agreement_body}": self._render_agreement(
                product_name=product_name,
                owner_email=owner_email,
                requested_by=requested_by,
            ),
        }
        rendered = template
        for key, value in replacements.items():
            rendered = rendered.replace(key, value)
        return rendered

    def send_consent_otp(self, *, product_name: str, owner_email: str, requested_by: str) -> dict:
        config = self.get_config()
        if not config["enabled"]:
            raise ValueError("Owner consent OTP is disabled in configuration.")
        normalized_owner_email = str(owner_email or "").strip().lower()
        normalized_requested_by = str(requested_by or "").strip().lower()
        if not product_name.strip() or not normalized_owner_email or not normalized_requested_by:
            raise ValueError("Product name, owner email, and requester email are required.")
        otp_length = max(4, min(config["otp_length"], 8))
        otp_code = "".join(str(random.randint(0, 9)) for _ in range(otp_length))
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=max(1, config["otp_expiry_minutes"]))
        runtime = self._read_runtime()
        consents = list(runtime.get("consents", []) or [])
        consent_key = self._build_consent_key(
            owner_email=normalized_owner_email,
            product_name=product_name,
            requested_by=normalized_requested_by,
        )
        existing = next((row for row in consents if str(row.get("consent_key", "")).strip() == consent_key), None)
        record = {
            "consent_key": consent_key,
            "product_name": str(product_name).strip(),
            "owner_email": normalized_owner_email,
            "requested_by": normalized_requested_by,
            "otp_code": otp_code,
            "otp_sent_at": now.isoformat(),
            "otp_expires_at": expires_at.isoformat(),
            "verified_at": "",
            "status": "OTP_SENT",
            "agreement_title": config["agreement_title"],
            "agreement_body": self._render_agreement(
                product_name=product_name,
                owner_email=normalized_owner_email,
                requested_by=normalized_requested_by,
            ),
        }
        if existing:
            existing.update(record)
        else:
            consents.append(record)
        runtime["consents"] = consents
        self._write_runtime(runtime)
        self.gmail_queue_service.enqueue(
            to_email=normalized_owner_email,
            subject=config["email_subject"],
            body=self._render_email_body(
                product_name=product_name,
                owner_email=normalized_owner_email,
                requested_by=normalized_requested_by,
                otp_code=otp_code,
            ),
        )
        try:
            self.gmail_delivery_service.process_queue(limit=10)
        except Exception:
            pass
        return record

    def verify_consent_otp(self, *, product_name: str, owner_email: str, requested_by: str, otp_code: str) -> dict:
        normalized_owner_email = str(owner_email or "").strip().lower()
        normalized_requested_by = str(requested_by or "").strip().lower()
        consent_key = self._build_consent_key(
            owner_email=normalized_owner_email,
            product_name=product_name,
            requested_by=normalized_requested_by,
        )
        runtime = self._read_runtime()
        consents = list(runtime.get("consents", []) or [])
        record = next((row for row in consents if str(row.get("consent_key", "")).strip() == consent_key), None)
        if not record:
            raise ValueError("Consent OTP was not sent for this owner and product.")
        if str(record.get("status", "")).strip().upper() == "VERIFIED":
            return record
        if str(record.get("otp_code", "")).strip() != str(otp_code or "").strip():
            raise ValueError("Invalid consent OTP.")
        expires_at = str(record.get("otp_expires_at", "")).strip()
        if expires_at and datetime.now(UTC) > datetime.fromisoformat(expires_at):
            record["status"] = "EXPIRED"
            self._write_runtime(runtime)
            raise ValueError("Consent OTP has expired.")
        record["status"] = "VERIFIED"
        record["verified_at"] = datetime.now(UTC).isoformat()
        self._write_runtime(runtime)
        return record

    def get_consent_status(self, *, product_name: str, owner_email: str, requested_by: str) -> dict:
        normalized_owner_email = str(owner_email or "").strip().lower()
        normalized_requested_by = str(requested_by or "").strip().lower()
        consent_key = self._build_consent_key(
            owner_email=normalized_owner_email,
            product_name=product_name,
            requested_by=normalized_requested_by,
        )
        runtime = self._read_runtime()
        consents = list(runtime.get("consents", []) or [])
        return next((row for row in consents if str(row.get("consent_key", "")).strip() == consent_key), {})

    def list_consents(self) -> list[dict]:
        return list((self._read_runtime().get("consents", []) or []))
