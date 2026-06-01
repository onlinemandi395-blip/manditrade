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

    @property
    def mahajans_path(self) -> Path:
        return self.governance_root / "mahajans.json"

    @property
    def raw_materials_path(self) -> Path:
        return self.governance_root / "raw_materials.json"

    @property
    def supply_orders_path(self) -> Path:
        return self.governance_root / "supply_orders.json"

    @property
    def supply_ledgers_path(self) -> Path:
        return self.governance_root / "supply_ledgers.json"

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
        if not self.mahajans_path.exists():
            self.safe_drive_write_service.replace_document(
                self.mahajans_path,
                {"schema_version": "1.0", "mahajans": []},
            )
        if not self.raw_materials_path.exists():
            self.safe_drive_write_service.replace_document(
                self.raw_materials_path,
                {"schema_version": "1.0", "raw_materials": []},
            )
        if not self.supply_orders_path.exists():
            self.safe_drive_write_service.replace_document(
                self.supply_orders_path,
                {"schema_version": "1.0", "supply_orders": []},
            )
        if not self.supply_ledgers_path.exists():
            self.safe_drive_write_service.replace_document(
                self.supply_ledgers_path,
                {"schema_version": "1.0", "entries": []},
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

    def list_mahajans(self) -> list[dict[str, Any]]:
        self.ensure_files()
        return self.json_service.read_json(self.mahajans_path, {"mahajans": []}).get("mahajans", [])

    def get_mahajan(self, mahajan_id: str) -> dict[str, Any] | None:
        self.ensure_files()
        return next((item for item in self.list_mahajans() if item.get("mahajan_id") == mahajan_id), None)

    def get_mahajan_by_email(self, email: str) -> dict[str, Any] | None:
        self.ensure_files()
        email_key = email.strip().lower()
        return next((item for item in self.list_mahajans() if item.get("email", "").strip().lower() == email_key), None)

    def upsert_mahajan(self, mahajan: dict[str, Any]) -> dict[str, Any]:
        self.ensure_files()
        payload = self.json_service.read_json(self.mahajans_path, {"mahajans": []})
        mahajan_id = str(mahajan.get("mahajan_id") or "").strip().upper()
        email = str(mahajan.get("email") or "").strip().lower()
        if not mahajan_id:
            raise ValueError("Mahajan ID is required.")
        if not email:
            raise ValueError("Mahajan email is required.")
        now = datetime.now(UTC).isoformat()
        existing = next((item for item in payload.get("mahajans", []) if item.get("mahajan_id") == mahajan_id), None)
        normalized = {
            "mahajan_id": mahajan_id,
            "business_name": str(mahajan.get("business_name") or (existing or {}).get("business_name") or "").strip(),
            "owner_name": str(mahajan.get("owner_name") or (existing or {}).get("owner_name") or "").strip(),
            "email": email,
            "mobile": str(mahajan.get("mobile") or (existing or {}).get("mobile") or "").strip(),
            "city": str(mahajan.get("city") or (existing or {}).get("city") or "").strip(),
            "status": str(mahajan.get("status") or (existing or {}).get("status") or "INVITED").strip().upper(),
            "notes": str(mahajan.get("notes") or (existing or {}).get("notes") or "").strip(),
            "created_at": (existing or {}).get("created_at") or now,
            "updated_at": now,
        }
        if existing:
            existing.update(normalized)
        else:
            payload.setdefault("mahajans", []).append(normalized)
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.mahajans_path, payload)
        return normalized

    def list_raw_materials(self, *, mahajan_id: str | None = None) -> list[dict[str, Any]]:
        self.ensure_files()
        rows = self.json_service.read_json(self.raw_materials_path, {"raw_materials": []}).get("raw_materials", [])
        if mahajan_id:
            return [item for item in rows if item.get("mahajan_id") == mahajan_id]
        return rows

    def upsert_raw_material(self, item: dict[str, Any]) -> dict[str, Any]:
        self.ensure_files()
        payload = self.json_service.read_json(self.raw_materials_path, {"raw_materials": []})
        material_id = str(item.get("raw_material_id") or "").strip().upper()
        if not material_id:
            raise ValueError("Raw material ID is required.")
        now = datetime.now(UTC).isoformat()
        existing = next((row for row in payload.get("raw_materials", []) if row.get("raw_material_id") == material_id), None)
        normalized = {
            "raw_material_id": material_id,
            "mahajan_id": str(item.get("mahajan_id") or (existing or {}).get("mahajan_id") or "").strip().upper(),
            "name": str(item.get("name") or (existing or {}).get("name") or "").strip(),
            "category": str(item.get("category") or (existing or {}).get("category") or "RAW_MATERIAL").strip().upper(),
            "unit": str(item.get("unit") or (existing or {}).get("unit") or "kg").strip(),
            "available_qty": int(item.get("available_qty") if item.get("available_qty") is not None else (existing or {}).get("available_qty", 0) or 0),
            "supply_price": round(float(item.get("supply_price") if item.get("supply_price") is not None else (existing or {}).get("supply_price", 0) or 0), 2),
            "status": str(item.get("status") or (existing or {}).get("status") or "ACTIVE").strip().upper(),
            "created_at": (existing or {}).get("created_at") or now,
            "updated_at": now,
        }
        if existing:
            existing.update(normalized)
        else:
            payload.setdefault("raw_materials", []).append(normalized)
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.raw_materials_path, payload)
        return normalized

    def list_supply_orders(self) -> list[dict[str, Any]]:
        self.ensure_files()
        return self.json_service.read_json(self.supply_orders_path, {"supply_orders": []}).get("supply_orders", [])

    def get_supply_order(self, order_id: str) -> dict[str, Any] | None:
        self.ensure_files()
        return next((item for item in self.list_supply_orders() if item.get("mandi_order_id") == order_id), None)

    def upsert_supply_order(self, order: dict[str, Any]) -> dict[str, Any]:
        self.ensure_files()
        payload = self.json_service.read_json(self.supply_orders_path, {"supply_orders": []})
        order_id = str(order.get("mandi_order_id") or "").strip().upper()
        if not order_id:
            raise ValueError("Mandi order ID is required.")
        now = datetime.now(UTC).isoformat()
        existing = next((row for row in payload.get("supply_orders", []) if row.get("mandi_order_id") == order_id), None)
        normalized = dict(existing or {})
        normalized.update(order)
        normalized["mandi_order_id"] = order_id
        normalized["updated_at"] = now
        normalized["created_at"] = normalized.get("created_at") or now
        if existing:
            existing.update(normalized)
        else:
            payload.setdefault("supply_orders", []).append(normalized)
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.supply_orders_path, payload)
        return normalized

    def list_supply_ledger_entries(self) -> list[dict[str, Any]]:
        self.ensure_files()
        return self.json_service.read_json(self.supply_ledgers_path, {"entries": []}).get("entries", [])

    def create_supply_ledger_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        self.ensure_files()
        payload = self.json_service.read_json(self.supply_ledgers_path, {"entries": []})
        payload.setdefault("entries", []).append(entry)
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.supply_ledgers_path, payload)
        return entry
