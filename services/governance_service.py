from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import re

from services.json_service import JsonService


class GovernanceService:
    def __init__(self, governance_root: Path, safe_drive_write_service) -> None:
        self.governance_root = governance_root
        self.json_service = JsonService()
        self.safe_drive_write_service = safe_drive_write_service

    @property
    def products_path(self) -> Path:
        return self.governance_root / "products.json"

    @property
    def manufacturers_path(self) -> Path:
        return self.governance_root / "manufacturers.json"

    @property
    def admin_profiles_path(self) -> Path:
        return self.governance_root / "admin_profiles.json"

    def ensure_files(self) -> None:
        if not self.products_path.exists():
            self.safe_drive_write_service.replace_document(
                self.products_path,
                {"schema_version": "1.0", "products": []},
                schema_name="products",
            )
        if not self.manufacturers_path.exists():
            self.safe_drive_write_service.replace_document(
                self.manufacturers_path,
                {"schema_version": "1.0", "manufacturers": []},
                schema_name="manufacturers",
            )
        if not self.admin_profiles_path.exists():
            self.safe_drive_write_service.replace_document(
                self.admin_profiles_path,
                {"schema_version": "1.0", "profiles": []},
            )

    def list_products(self) -> list[dict[str, Any]]:
        self.ensure_files()
        return self.json_service.read_json(self.products_path, {"products": []}).get("products", [])

    def upsert_product(self, product: dict[str, Any]) -> None:
        self.ensure_files()
        payload = self.json_service.read_json(self.products_path, {"products": []})
        products = payload.get("products", [])
        product_key = product.get("product_id") or product.get("product_code")
        existing = next(
            (
                item
                for item in products
                if (item.get("product_id") or item.get("product_code")) == product_key
            ),
            None,
        )
        if existing:
            existing.update(product)
        else:
            products.append(product)
        payload["products"] = products
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.products_path, payload, schema_name="products")

    def delete_product(self, product_id: str) -> bool:
        self.ensure_files()
        payload = self.json_service.read_json(self.products_path, {"products": []})
        original_count = len(payload.get("products", []))
        payload["products"] = [
            item
            for item in payload.get("products", [])
            if (item.get("product_id") or item.get("product_code")) != product_id
        ]
        if len(payload["products"]) == original_count:
            return False
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.products_path, payload, schema_name="products")
        return True

    def list_manufacturers(self) -> list[dict[str, Any]]:
        self.ensure_files()
        return self.json_service.read_json(self.manufacturers_path, {"manufacturers": []}).get("manufacturers", [])

    def register_manufacturer(self, manufacturer: dict[str, Any]) -> None:
        self.ensure_files()
        payload = self.json_service.read_json(self.manufacturers_path, {"manufacturers": []})
        manufacturers = payload.get("manufacturers", [])
        manufacturer_code = str(manufacturer.get("manufacturer_code") or "").strip().upper()
        if not manufacturer_code:
            raise ValueError("Manufacturer code is required.")
        existing = next(
            (item for item in manufacturers if item["manufacturer_code"] == manufacturer_code),
            None,
        )
        if existing and existing.get("manufacturer_id") != manufacturer.get("manufacturer_id"):
            raise ValueError(f"Manufacturer code already exists: {manufacturer_code}")
        if existing:
            existing.update(manufacturer)
        else:
            manufacturers.append(manufacturer)
        payload["manufacturers"] = manufacturers
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.manufacturers_path, payload, schema_name="manufacturers")

    def get_manufacturer(self, manufacturer_code: str) -> dict[str, Any] | None:
        self.ensure_files()
        manufacturers = self.json_service.read_json(self.manufacturers_path, {"manufacturers": []}).get("manufacturers", [])
        return next((item for item in manufacturers if item.get("manufacturer_code") == manufacturer_code), None)

    def update_manufacturer(self, manufacturer_code: str, updates: dict[str, Any]) -> dict[str, Any]:
        self.ensure_files()
        payload = self.json_service.read_json(self.manufacturers_path, {"manufacturers": []})
        updated: dict[str, Any] | None = None
        for item in payload.get("manufacturers", []):
            if item.get("manufacturer_code") == manufacturer_code:
                item.update(updates)
                item["updated_at"] = datetime.now(UTC).isoformat()
                updated = dict(item)
                break
        if updated is None:
            raise ValueError(f"Manufacturer not found: {manufacturer_code}")
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.manufacturers_path, payload, schema_name="manufacturers")
        return updated

    def delete_manufacturer(self, manufacturer_code: str) -> bool:
        self.ensure_files()
        payload = self.json_service.read_json(self.manufacturers_path, {"manufacturers": []})
        original_count = len(payload.get("manufacturers", []))
        payload["manufacturers"] = [item for item in payload.get("manufacturers", []) if item.get("manufacturer_code") != manufacturer_code]
        if len(payload["manufacturers"]) == original_count:
            return False
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.manufacturers_path, payload, schema_name="manufacturers")
        return True

    def update_manufacturer_status(self, manufacturer_code: str, status: str, subscription_plan: str | None = None) -> None:
        self.ensure_files()
        payload = self.json_service.read_json(self.manufacturers_path, {"manufacturers": []})
        for item in payload.get("manufacturers", []):
            if item["manufacturer_code"] == manufacturer_code:
                item["status"] = status
                if subscription_plan:
                    item["subscription_plan"] = subscription_plan
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.manufacturers_path, payload, schema_name="manufacturers")

    def generate_next_manufacturer_code(self) -> str:
        self.ensure_files()
        manufacturers = self.list_manufacturers()
        highest_suffix = 0
        for item in manufacturers:
            code = str(item.get("manufacturer_code") or "").strip().upper()
            match = re.fullmatch(r"MANU(\d+)", code)
            if match:
                highest_suffix = max(highest_suffix, int(match.group(1)))
        return f"MANU{highest_suffix + 1:03d}"

    def list_admin_profiles(self) -> list[dict[str, Any]]:
        self.ensure_files()
        return self.json_service.read_json(self.admin_profiles_path, {"profiles": []}).get("profiles", [])

    def get_admin_profile(self, email: str) -> dict[str, Any] | None:
        self.ensure_files()
        email_key = email.strip().lower()
        profiles = self.json_service.read_json(self.admin_profiles_path, {"profiles": []}).get("profiles", [])
        return next((item for item in profiles if item.get("email", "").strip().lower() == email_key), None)

    def upsert_admin_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        self.ensure_files()
        now = datetime.now(UTC).isoformat()
        email_key = str(profile.get("email") or "").strip().lower()
        if not email_key:
            raise ValueError("Admin profile email is required.")
        payload = self.json_service.read_json(self.admin_profiles_path, {"profiles": []})
        existing = next((item for item in payload.get("profiles", []) if item.get("email", "").strip().lower() == email_key), None)
        normalized = {
            "schema_version": "1.0",
            "email": email_key,
            "full_name": str(profile.get("full_name") or (existing or {}).get("full_name") or "").strip(),
            "mobile": str(profile.get("mobile") or (existing or {}).get("mobile") or "").strip(),
            "alternate_mobile": str(profile.get("alternate_mobile") or (existing or {}).get("alternate_mobile") or "").strip(),
            "designation": str(profile.get("designation") or (existing or {}).get("designation") or "").strip(),
            "office_name": str(profile.get("office_name") or (existing or {}).get("office_name") or "").strip(),
            "address": {
                "line1": str(((profile.get("address") or {}).get("line1")) or ((existing or {}).get("address", {}) or {}).get("line1") or "").strip(),
                "line2": str(((profile.get("address") or {}).get("line2")) or ((existing or {}).get("address", {}) or {}).get("line2") or "").strip(),
                "city": str(((profile.get("address") or {}).get("city")) or ((existing or {}).get("address", {}) or {}).get("city") or "").strip(),
                "state": str(((profile.get("address") or {}).get("state")) or ((existing or {}).get("address", {}) or {}).get("state") or "").strip(),
                "pin_code": str(((profile.get("address") or {}).get("pin_code")) or ((existing or {}).get("address", {}) or {}).get("pin_code") or "").strip(),
            },
            "support_email": str(profile.get("support_email") or (existing or {}).get("support_email") or "").strip(),
            "notification_email": str(profile.get("notification_email") or (existing or {}).get("notification_email") or "").strip(),
            "credential_reference": str(profile.get("credential_reference") or (existing or {}).get("credential_reference") or "").strip(),
            "credential_notes": str(profile.get("credential_notes") or (existing or {}).get("credential_notes") or "").strip(),
            "profile_notes": str(profile.get("profile_notes") or (existing or {}).get("profile_notes") or "").strip(),
            "created_at": (existing or {}).get("created_at") or profile.get("created_at") or now,
            "updated_at": now,
        }
        if existing:
            existing.update(normalized)
        else:
            payload.setdefault("profiles", []).append(normalized)
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.admin_profiles_path, payload)
        return normalized
