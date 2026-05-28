from __future__ import annotations

import secrets
import shutil
import re
from datetime import UTC, datetime
from typing import Any


class ManufacturerOnboardingService:
    def __init__(self, drive_service, governance_service, safe_drive_write_service, json_service, id_allocator_service=None) -> None:
        self.drive_service = drive_service
        self.governance_service = governance_service
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.id_allocator_service = id_allocator_service

    def generate_onboarding_secret(self) -> str:
        return f"MANU-SETUP-{secrets.token_urlsafe(18)}"

    def build_onboarding_steps(self, manufacturer: dict[str, Any]) -> str:
        code = manufacturer["manufacturer_code"]
        secret = manufacturer.get("manufacturer_onboarding_secret", "")
        owner_email = manufacturer.get("owner_email", "")
        return (
            f"Manufacturer onboarding for {code}\n\n"
            f"1. Sign in to MandiTrade with Google using {owner_email or 'the approved manufacturer email'}.\n"
            f"2. Share your manufacturer code with admin: {code}\n"
            f"3. Share your first-time manufacturer onboarding secret with admin: {secret}\n"
            f"4. Ask admin to map your Google account to this manufacturer workspace.\n"
            f"5. After account mapping, start with Products, Inventory, Clients, and Mandi RFQ.\n\n"
            f"Admin checklist:\n"
            f"- Verify Google email matches expected owner email.\n"
            f"- Confirm secret matches the onboarding packet.\n"
            f"- Ensure manufacturer status stays ACTIVE.\n"
            f"- Share post-onboarding navigation: Products, Inventory, Client Orders, Mandi RFQ, Ledger / Khata."
        )

    def create_manufacturer(
        self,
        *,
        manufacturer_code: str,
        manufacturer_name: str = "",
        business_name: str = "",
        owner_name: str = "",
        owner_email: str,
        mobile: str = "",
        alternate_mobile: str = "",
        address_line1: str = "",
        address_line2: str = "",
        city: str,
        state: str = "",
        pin_code: str = "",
        business_type: str = "",
        product_categories: list[str] | None = None,
        udyam_id: str = "",
        gstin: str = "",
        pan: str = "",
        aadhaar: str = "",
        bank_account_holder_name: str = "",
        bank_account_number: str = "",
        ifsc_code: str = "",
        upi_id: str = "",
        google_drive_connected_status: str = "NOT_CONNECTED",
        business_description: str = "",
        created_by: str,
        subscription_plan: str = "basic",
    ) -> dict[str, Any]:
        normalized_code = manufacturer_code.strip().upper()
        normalized_business_name = (business_name or manufacturer_name).strip()
        paths = self.drive_service.initialize_manufacturer_workspace(
            manufacturer_code=normalized_code,
            manufacturer_name=normalized_business_name,
            owner_email=owner_email.strip(),
            city=city.strip(),
            status="ACTIVE",
        )
        onboarding_secret = self.generate_onboarding_secret()
        manufacturer = self._build_manufacturer_record(
            payload={
                "manufacturer_code": normalized_code,
                "manufacturer_name": normalized_business_name,
                "business_name": normalized_business_name,
                "owner_name": owner_name,
                "owner_email": owner_email,
                "mobile": mobile,
                "alternate_mobile": alternate_mobile,
                "address": {
                    "line1": address_line1,
                    "line2": address_line2,
                    "city": city,
                    "state": state,
                    "pin_code": pin_code,
                },
                "business_type": business_type,
                "product_categories": product_categories or [],
                "legal": {
                    "udyam_id": udyam_id,
                    "gstin": gstin,
                    "pan": pan,
                    "aadhaar": aadhaar,
                },
                "banking": {
                    "account_holder_name": bank_account_holder_name,
                    "account_number": bank_account_number,
                    "ifsc": ifsc_code,
                    "upi_id": upi_id,
                },
                "google_drive_connected_status": google_drive_connected_status,
                "business_description": business_description,
                "status": "ACTIVE",
                "subscription_plan": subscription_plan,
                "manufacturer_onboarding_secret": onboarding_secret,
                "created_by": created_by,
            },
            workspace_paths=paths,
        )
        manufacturer["manufacturer_onboarding_steps"] = self.build_onboarding_steps(manufacturer)
        self.governance_service.register_manufacturer(manufacturer)
        self._sync_workspace_config(manufacturer)
        return manufacturer

    def update_manufacturer(self, manufacturer_code: str, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.governance_service.get_manufacturer(manufacturer_code)
        if current is None:
            raise ValueError(f"Manufacturer not found: {manufacturer_code}")
        merged = self._deep_merge(dict(current), {key: value for key, value in updates.items() if value is not None})
        merged = self._build_manufacturer_record(
            payload=merged,
            workspace_paths=self.drive_service.get_manufacturer_paths(manufacturer_code),
            existing=current,
        )
        merged["manufacturer_onboarding_steps"] = self.build_onboarding_steps(merged)
        updated = self.governance_service.update_manufacturer(manufacturer_code, merged)
        self._sync_workspace_config(updated)
        return updated

    def regenerate_secret(self, manufacturer_code: str) -> dict[str, Any]:
        secret = self.generate_onboarding_secret()
        return self.update_manufacturer(manufacturer_code, {"manufacturer_onboarding_secret": secret})

    def delete_manufacturer(self, manufacturer_code: str, *, remove_workspace: bool = False) -> bool:
        removed = self.governance_service.delete_manufacturer(manufacturer_code)
        if removed and remove_workspace:
            workspace_root = self.drive_service.get_manufacturer_paths(manufacturer_code).manufacturer_root
            if workspace_root.exists():
                shutil.rmtree(workspace_root)
        return removed

    def _sync_workspace_config(self, manufacturer: dict[str, Any]) -> None:
        config_path = self.drive_service.get_manufacturer_paths(manufacturer["manufacturer_code"]).private_zone / "manufacturer_config.json"
        payload = self.json_service.read_json(config_path, {"schema_version": "1.0"})
        payload.update(
            {
                "schema_version": "1.0",
                "manufacturer_id": manufacturer.get("manufacturer_id", ""),
                "manufacturer_code": manufacturer["manufacturer_code"],
                "manufacturer_name": manufacturer.get("manufacturer_name", ""),
                "business_name": manufacturer.get("business_name", ""),
                "owner_name": manufacturer.get("owner_name", ""),
                "owner_email": manufacturer.get("owner_email", ""),
                "mobile": manufacturer.get("mobile", ""),
                "alternate_mobile": manufacturer.get("alternate_mobile", ""),
                "address": manufacturer.get("address", {}),
                "city": manufacturer.get("address", {}).get("city", manufacturer.get("city", "")),
                "state": manufacturer.get("address", {}).get("state", ""),
                "pin_code": manufacturer.get("address", {}).get("pin_code", ""),
                "business_type": manufacturer.get("business_type", ""),
                "product_categories": manufacturer.get("product_categories", []),
                "legal": manufacturer.get("legal", {}),
                "banking": manufacturer.get("banking", {}),
                "google_drive_connected_status": manufacturer.get("google_drive_connected_status", "NOT_CONNECTED"),
                "business_description": manufacturer.get("business_description", ""),
                "status": manufacturer.get("status", "ACTIVE"),
                "subscription_plan": manufacturer.get("subscription_plan", "basic"),
                "manufacturer_onboarding_secret": manufacturer.get("manufacturer_onboarding_secret", ""),
                "workspace": manufacturer.get("workspace", {}),
            }
        )
        self.safe_drive_write_service.replace_document(config_path, payload)

    def _build_manufacturer_record(self, *, payload: dict[str, Any], workspace_paths, existing: dict[str, Any] | None = None) -> dict[str, Any]:
        existing = existing or {}
        address = payload.get("address", {}) or {}
        legal = payload.get("legal", {}) or {}
        banking = payload.get("banking", {}) or {}
        now = datetime.now(UTC).isoformat()
        manufacturer_code = str(payload.get("manufacturer_code") or existing.get("manufacturer_code") or "").strip().upper()
        business_name = str(payload.get("business_name") or payload.get("manufacturer_name") or existing.get("business_name") or existing.get("manufacturer_name") or "").strip()
        owner_name = str(payload.get("owner_name") or existing.get("owner_name") or "").strip()
        owner_email = str(payload.get("owner_email") or existing.get("owner_email") or "").strip().lower()
        mobile = str(payload.get("mobile") or existing.get("mobile") or "").strip()
        alternate_mobile = str(payload.get("alternate_mobile") or existing.get("alternate_mobile") or "").strip()
        normalized_address = {
            "line1": str(address.get("line1") or existing.get("address", {}).get("line1") or "").strip(),
            "line2": str(address.get("line2") or existing.get("address", {}).get("line2") or "").strip(),
            "city": str(address.get("city") or payload.get("city") or existing.get("address", {}).get("city") or existing.get("city") or "").strip(),
            "state": str(address.get("state") or payload.get("state") or existing.get("address", {}).get("state") or "").strip(),
            "pin_code": str(address.get("pin_code") or payload.get("pin_code") or existing.get("address", {}).get("pin_code") or "").strip(),
        }
        product_categories = payload.get("product_categories", existing.get("product_categories", [])) or []
        if isinstance(product_categories, str):
            product_categories = [item.strip() for item in product_categories.split(",") if item.strip()]
        else:
            product_categories = [str(item).strip() for item in product_categories if str(item).strip()]
        normalized_legal = {
            "udyam_id": str(legal.get("udyam_id") or existing.get("legal", {}).get("udyam_id") or "").strip(),
            "gstin": str(legal.get("gstin") or existing.get("legal", {}).get("gstin") or "").strip().upper(),
            "pan": str(legal.get("pan") or existing.get("legal", {}).get("pan") or "").strip().upper(),
            "aadhaar": re.sub(r"\D", "", str(legal.get("aadhaar") or existing.get("legal", {}).get("aadhaar") or "").strip()),
        }
        normalized_banking = {
            "account_holder_name": str(banking.get("account_holder_name") or existing.get("banking", {}).get("account_holder_name") or "").strip(),
            "account_number": str(banking.get("account_number") or existing.get("banking", {}).get("account_number") or "").strip(),
            "ifsc": str(banking.get("ifsc") or existing.get("banking", {}).get("ifsc") or "").strip().upper(),
            "upi_id": str(banking.get("upi_id") or existing.get("banking", {}).get("upi_id") or "").strip(),
        }
        errors = self._validate_manufacturer_fields(
            business_name=business_name,
            owner_name=owner_name,
            owner_email=owner_email,
            mobile=mobile,
            city=normalized_address["city"],
            state=normalized_address["state"],
            pin_code=normalized_address["pin_code"],
            gstin=normalized_legal["gstin"],
            pan=normalized_legal["pan"],
            aadhaar=normalized_legal["aadhaar"],
            ifsc=normalized_banking["ifsc"],
        )
        if errors:
            raise ValueError("\n".join(errors))
        manufacturer_id = existing.get("manufacturer_id") or payload.get("manufacturer_id")
        if not manufacturer_id:
            manufacturer_id = self.id_allocator_service.allocate("manufacturer") if self.id_allocator_service else f"MANU-{datetime.now(UTC).year}-{manufacturer_code[-6:] or '000001'}"
        record = {
            "manufacturer_id": manufacturer_id,
            "manufacturer_code": manufacturer_code,
            "business_name": business_name,
            "manufacturer_name": business_name,
            "owner_name": owner_name,
            "owner_email": owner_email,
            "mobile": mobile,
            "alternate_mobile": alternate_mobile,
            "address": normalized_address,
            "city": normalized_address["city"],
            "business_type": str(payload.get("business_type") or existing.get("business_type") or "").strip(),
            "product_categories": product_categories,
            "legal": normalized_legal,
            "banking": normalized_banking,
            "google_drive_connected_status": str(payload.get("google_drive_connected_status") or existing.get("google_drive_connected_status") or "NOT_CONNECTED").strip().upper(),
            "business_description": str(payload.get("business_description") or existing.get("business_description") or "").strip(),
            "status": str(payload.get("status") or existing.get("status") or "ACTIVE").strip().upper(),
            "created_at": existing.get("created_at") or payload.get("created_at") or now,
            "updated_at": now,
            "created_by": existing.get("created_by") or payload.get("created_by") or "",
            "subscription_plan": str(payload.get("subscription_plan") or existing.get("subscription_plan") or "basic").strip(),
            "manufacturer_onboarding_secret": str(payload.get("manufacturer_onboarding_secret") or existing.get("manufacturer_onboarding_secret") or "").strip(),
            "workspace": {
                "root": str(workspace_paths.manufacturer_root),
                "shared_zone": str(workspace_paths.shared_zone),
                "private_zone": str(workspace_paths.private_zone),
            },
            "workspace_root": str(workspace_paths.manufacturer_root),
            "shared_zone": str(workspace_paths.shared_zone),
            "private_zone": str(workspace_paths.private_zone),
        }
        return record

    def _validate_manufacturer_fields(
        self,
        *,
        business_name: str,
        owner_name: str,
        owner_email: str,
        mobile: str,
        city: str,
        state: str,
        pin_code: str,
        gstin: str,
        pan: str,
        aadhaar: str,
        ifsc: str,
    ) -> list[str]:
        errors: list[str] = []
        if not business_name:
            errors.append("Business / Manufacturer Name is required.")
        if not owner_name:
            errors.append("Owner Name is required.")
        if not owner_email:
            errors.append("Owner Email is required.")
        if not mobile:
            errors.append("Mobile Number is required.")
        if not city:
            errors.append("City is required.")
        if not state:
            errors.append("State is required.")
        if not pin_code:
            errors.append("PIN Code is required.")
        if mobile and not re.fullmatch(r"\d{10}", re.sub(r"\D", "", mobile)):
            errors.append("Mobile Number must be 10 digits.")
        if pin_code and not re.fullmatch(r"\d{6}", pin_code):
            errors.append("PIN Code must be 6 digits.")
        if gstin and len(gstin) != 15:
            errors.append("GSTIN must be 15 characters if provided.")
        if pan and len(pan) != 10:
            errors.append("PAN Number must be 10 characters if provided.")
        if aadhaar and not re.fullmatch(r"\d{12}", aadhaar):
            errors.append("Aadhaar Number must be 12 digits if provided.")
        if ifsc and len(ifsc) != 11:
            errors.append("IFSC Code must be 11 characters if provided.")
        return errors

    def _deep_merge(self, current: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
        merged = dict(current)
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged
