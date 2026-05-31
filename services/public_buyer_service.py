from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class PublicBuyerService:
    REQUIRED_PROFILE_FIELDS = ("full_name", "mobile", "city", "state", "pin_code", "delivery_address")
    VALID_PAYMENT_MODES = ("UPI", "Cash", "Card", "Net Banking")

    def __init__(self, public_buyers_root: Path, safe_drive_write_service, json_service, id_allocator_service) -> None:
        self.public_buyers_root = public_buyers_root
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.id_allocator_service = id_allocator_service

    @property
    def index_path(self) -> Path:
        return self.public_buyers_root / "index.json"

    def ensure_files(self) -> None:
        self.public_buyers_root.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self.safe_drive_write_service.replace_document(
                self.index_path,
                {"schema_version": "1.0", "buyers": []},
            )

    def profile_path(self, public_buyer_id: str) -> Path:
        return self.public_buyers_root / f"{public_buyer_id}.json"

    def notifications_path(self, public_buyer_id: str) -> Path:
        return self.public_buyers_root / public_buyer_id / "notifications.json"

    def cart_path(self, public_buyer_id: str) -> Path:
        return self.public_buyers_root / public_buyer_id / "cart.json"

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        self.ensure_files()
        email_key = email.strip().lower()
        index = self.json_service.read_json(self.index_path, {"buyers": []}).get("buyers", [])
        buyer = next((item for item in index if item.get("email", "").strip().lower() == email_key), None)
        if not buyer:
            return None
        return self.get_by_id(buyer["public_buyer_id"])

    def get_by_id(self, public_buyer_id: str) -> dict[str, Any] | None:
        self.ensure_files()
        path = self.profile_path(public_buyer_id)
        if not path.exists():
            return None
        return self.json_service.read_json(path, {})

    def register_or_get(self, *, email: str, full_name: str = "") -> dict[str, Any]:
        existing = self.get_by_email(email)
        if existing:
            return existing
        now = datetime.now(UTC).isoformat()
        public_buyer_id = self.id_allocator_service.allocate("public_buyer")
        profile = {
            "schema_version": "1.0",
            "public_buyer_id": public_buyer_id,
            "email": email.strip().lower(),
            "full_name": full_name.strip(),
            "mobile": "",
            "alternate_mobile": "",
            "business_name": "",
            "city": "",
            "state": "",
            "pin_code": "",
            "delivery_address": "",
            "landmark": "",
            "preferred_payment_mode": "UPI",
            "delivery_instructions": "",
            "address": {
                "line1": "",
                "line2": "",
                "city": "",
                "state": "",
                "pin_code": "",
                "landmark": "",
            },
            "profile_status": "INCOMPLETE",
            "status": "ACTIVE",
            "created_at": now,
            "updated_at": now,
        }
        self.safe_drive_write_service.replace_document(self.profile_path(public_buyer_id), profile)
        self.safe_drive_write_service.append_record(
            self.index_path,
            "buyers",
            {
                "public_buyer_id": public_buyer_id,
                "email": profile["email"],
                "full_name": profile["full_name"],
                "status": "ACTIVE",
                "created_at": now,
                "updated_at": now,
            },
        )
        return profile

    def upsert_profile(self, public_buyer_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        profile = self.get_by_id(public_buyer_id)
        if profile is None:
            raise ValueError(f"Public buyer not found: {public_buyer_id}")
        merged = self._normalize_profile({**dict(profile), **updates}, existing=profile)
        self.validate_profile(merged)
        merged["public_buyer_id"] = public_buyer_id
        merged["email"] = str(merged.get("email", profile.get("email", ""))).strip().lower()
        merged["updated_at"] = datetime.now(UTC).isoformat()
        self.safe_drive_write_service.replace_document(self.profile_path(public_buyer_id), merged)
        self.safe_drive_write_service.update_record(
            self.index_path,
            "buyers",
            matcher=lambda item: item.get("public_buyer_id") == public_buyer_id,
            updater=lambda item: {
                **item,
                "email": merged["email"],
                "full_name": merged.get("full_name", ""),
                "status": merged.get("status", "ACTIVE"),
                "updated_at": merged["updated_at"],
            },
        )
        return merged

    def is_profile_complete(self, profile: dict[str, Any] | None) -> bool:
        if not profile:
            return False
        return bool(profile.get("profile_status") == "COMPLETE")

    def validate_profile(self, payload: dict[str, Any]) -> None:
        mobile = str(payload.get("mobile", "")).strip()
        pin_code = str(payload.get("pin_code", "")).strip()
        if not all(str(payload.get(field, "")).strip() for field in self.REQUIRED_PROFILE_FIELDS):
            raise ValueError("Full Name, Mobile, City, State, PIN Code, and Delivery Address are required.")
        if not (mobile.isdigit() and len(mobile) == 10):
            raise ValueError("Mobile number must be exactly 10 digits.")
        alternate_mobile = str(payload.get("alternate_mobile", "")).strip()
        if alternate_mobile and not (alternate_mobile.isdigit() and len(alternate_mobile) == 10):
            raise ValueError("Alternate mobile number must be exactly 10 digits.")
        if not (pin_code.isdigit() and len(pin_code) == 6):
            raise ValueError("PIN Code must be exactly 6 digits.")
        payment_mode = str(payload.get("preferred_payment_mode", "UPI")).strip()
        if payment_mode not in self.VALID_PAYMENT_MODES:
            raise ValueError("Preferred payment mode is invalid.")

    def _deep_merge(self, current: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
        merged = dict(current)
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    def _normalize_profile(self, payload: dict[str, Any], *, existing: dict[str, Any] | None = None) -> dict[str, Any]:
        existing = existing or {}
        address = payload.get("address", {}) or existing.get("address", {}) or {}
        delivery_address = str(payload.get("delivery_address") or address.get("line1") or "").strip()
        city = str(payload.get("city") or address.get("city") or "").strip()
        state = str(payload.get("state") or address.get("state") or "").strip()
        pin_code = str(payload.get("pin_code") or address.get("pin_code") or "").strip()
        landmark = str(payload.get("landmark") or address.get("landmark") or "").strip()
        normalized = {
            **existing,
            **payload,
            "email": str(payload.get("email") or existing.get("email") or "").strip().lower(),
            "full_name": str(payload.get("full_name") or existing.get("full_name") or "").strip(),
            "mobile": str(payload.get("mobile") or existing.get("mobile") or "").strip(),
            "alternate_mobile": str(payload.get("alternate_mobile") or existing.get("alternate_mobile") or "").strip(),
            "business_name": str(payload.get("business_name") or existing.get("business_name") or "").strip(),
            "city": city,
            "state": state,
            "pin_code": pin_code,
            "delivery_address": delivery_address,
            "landmark": landmark,
            "preferred_payment_mode": str(payload.get("preferred_payment_mode") or existing.get("preferred_payment_mode") or "UPI").strip() or "UPI",
            "delivery_instructions": str(payload.get("delivery_instructions") or existing.get("delivery_instructions") or "").strip(),
            "address": {
                "line1": delivery_address,
                "line2": "",
                "city": city,
                "state": state,
                "pin_code": pin_code,
                "landmark": landmark,
            },
        }
        normalized["profile_status"] = "COMPLETE" if self._has_required_profile_fields(normalized) else "INCOMPLETE"
        return normalized

    def _has_required_profile_fields(self, payload: dict[str, Any]) -> bool:
        return all(str(payload.get(field, "")).strip() for field in self.REQUIRED_PROFILE_FIELDS)
