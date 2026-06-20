from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from services.user_profile_service import UserProfileService


class AddressBookService:
    ADDRESS_FIELDS = (
        "address_line_1",
        "address_line_2",
        "city",
        "district",
        "state",
        "pin_code",
        "landmark",
    )

    def __init__(self, data_service) -> None:
        self.data_service = data_service
        self.user_profile_service = UserProfileService(data_service)

    def _normalize_email(self, email: str) -> str:
        return str(email or "").strip().lower()

    def _sanitize_address(self, address: dict | None) -> dict:
        payload = dict(address or {})
        return {
            "address_id": str(payload.get("address_id", "")).strip(),
            "label": str(payload.get("label", "")).strip(),
            "address_line_1": str(payload.get("address_line_1", "")).strip(),
            "address_line_2": str(payload.get("address_line_2", "")).strip(),
            "city": str(payload.get("city", "")).strip(),
            "district": str(payload.get("district", "")).strip(),
            "state": str(payload.get("state", "")).strip(),
            "pin_code": str(payload.get("pin_code", "")).strip(),
            "landmark": str(payload.get("landmark", "")).strip(),
        }

    def _get_user_record(self, email: str) -> dict | None:
        normalized_email = self._normalize_email(email)
        if not normalized_email:
            return None
        users = self.data_service.get_collection_ref("users")
        return next((row for row in users if self._normalize_email(row.get("email", "")) == normalized_email), None)

    def get_or_create_user_record(self, *, email: str, role: str, display_name: str, mobile: str = "") -> dict:
        normalized_email = self._normalize_email(email)
        if not normalized_email:
            raise ValueError("User email is required.")
        record = self._get_user_record(normalized_email)
        if record:
            if str(display_name or "").strip():
                record["display_name"] = str(display_name).strip()
            record["role"] = str(record.get("role", role or "public_buyer")).strip() or str(role or "public_buyer").strip() or "public_buyer"
            record["status"] = str(record.get("status", "ACTIVE")).strip() or "ACTIVE"
            if mobile is not None and str(mobile).strip():
                record["mobile"] = str(mobile).strip()
            record.setdefault("addresses", [])
            return record
        return self.data_service.upsert_user(
            {
                "user_id": self.data_service.id_service.next("user"),
                "email": normalized_email,
                "role": str(role or "public_buyer").strip() or "public_buyer",
                "status": "ACTIVE",
                "display_name": str(display_name or normalized_email.split("@")[0]).strip(),
                "mobile": str(mobile or "").strip(),
                "addresses": [],
            }
        )

    def list_addresses(self, email: str) -> list[dict]:
        profile = self.user_profile_service.get_profile(email)
        return [
            self._sanitize_address(address)
            for address in (profile.get("addresses", []) or [])
            if any(str((address or {}).get(field, "")).strip() for field in self.ADDRESS_FIELDS)
        ]

    def save_address(
        self,
        *,
        email: str,
        role: str,
        display_name: str,
        mobile: str,
        address: dict,
        address_id: str = "",
        label: str = "",
    ) -> dict:
        normalized_email = self._normalize_email(email)
        if not normalized_email:
            raise ValueError("User email is required to save address.")
        sanitized_address = self._sanitize_address(address)
        record = self.get_or_create_user_record(
            email=normalized_email,
            role=role,
            display_name=display_name,
            mobile=mobile,
        )
        profile = self.user_profile_service.get_or_create_profile(
            email=normalized_email,
            role=role,
            display_name=display_name,
            mobile=mobile,
        )

        normalized_address_id = str(address_id or sanitized_address.get("address_id", "")).strip()
        if not normalized_address_id:
            normalized_address_id = f"ADDR_{uuid4().hex[:10].upper()}"
        next_record = {
            **sanitized_address,
            "address_id": normalized_address_id,
            "label": str(label or sanitized_address.get("label", "") or "Saved Address").strip(),
        }
        addresses = list(profile.get("addresses", []) or [])
        existing = next(
            (item for item in addresses if str((item or {}).get("address_id", "")).strip() == normalized_address_id),
            None,
        )
        if existing:
            existing.update(next_record)
        else:
            addresses.append(next_record)
        profile["addresses"] = addresses
        profile["mobile"] = str(mobile or profile.get("mobile", "")).strip()
        profile["display_name"] = str(display_name or profile.get("display_name", "")).strip()
        self.user_profile_service.save_profile(
            actor_email=normalized_email,
            actor_role=role,
            target_email=normalized_email,
            updates=profile,
        )
        record["mobile"] = str(mobile or record.get("mobile", "")).strip()
        record["profile_path"] = self.user_profile_service._profile_logical_path(normalized_email)  # noqa: SLF001
        record["profile_folder"] = self.user_profile_service._workspace_logical_path(normalized_email)  # noqa: SLF001
        return deepcopy(next_record)
