from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import re

from services.json_service import JsonService


class GovernanceService:
    def __init__(self, governance_root: Path, safe_drive_write_service, audit_service=None, event_notification_service=None) -> None:
        self.governance_root = governance_root
        self.json_service = JsonService()
        self.safe_drive_write_service = safe_drive_write_service
        self.audit_service = audit_service
        self.event_notification_service = event_notification_service

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

    @property
    def mandiplace_orders_path(self) -> Path:
        return self.governance_root / "mandiplace_orders.json"

    @property
    def packaging_services_path(self) -> Path:
        return self.governance_root / "packaging_services.json"

    @property
    def courier_services_path(self) -> Path:
        return self.governance_root / "courier_services.json"

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
        if not self.mandiplace_orders_path.exists():
            self.safe_drive_write_service.replace_document(
                self.mandiplace_orders_path,
                {"schema_version": "1.0", "orders": []},
            )
        if not self.packaging_services_path.exists():
            self.safe_drive_write_service.replace_document(
                self.packaging_services_path,
                {"schema_version": "1.0", "services": []},
            )
        if not self.courier_services_path.exists():
            self.safe_drive_write_service.replace_document(
                self.courier_services_path,
                {"schema_version": "1.0", "services": []},
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
        self._audit("UPSERT_PRODUCT", "product", str(product_key), {"status": str((existing or product).get("status", ""))})

    def delete_product(self, product_id: str) -> bool:
        return self._archive_record(
            path=self.products_path,
            list_key="products",
            matcher=lambda item: (item.get("product_id") or item.get("product_code")) == product_id,
            entity_type="product",
            entity_id=product_id,
            extra_updates={"visible": False},
        )

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
        self._audit("UPSERT_MANUFACTURER", "manufacturer", manufacturer_code, {"status": str((existing or manufacturer).get("status", ""))})
        self._emit_event(
            "MANUFACTURER_UPDATED" if existing else "MANUFACTURER_CREATED",
            entity_type="MANUFACTURER",
            entity_id=manufacturer_code,
            title="Manufacturer saved",
            message=f"Manufacturer {manufacturer_code} was {'updated' if existing else 'created'}.",
            manufacturer_code=manufacturer_code,
            manufacturer_email=str((existing or manufacturer).get("owner_email", "")).strip().lower(),
        )

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
        return self._archive_record(
            path=self.manufacturers_path,
            list_key="manufacturers",
            matcher=lambda item: item.get("manufacturer_code") == manufacturer_code,
            entity_type="manufacturer",
            entity_id=manufacturer_code,
        )

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
        self._audit("UPSERT_MAHAJAN", "mahajan", mahajan_id, {"status": normalized.get("status", "")})
        self._emit_event(
            "MAHAJAN_ONBOARDED" if not existing else "STATUS_CHANGED",
            entity_type="MAHAJAN",
            entity_id=mahajan_id,
            title="Mahajan saved",
            message=f"Mahajan {mahajan_id} was {'onboarded' if not existing else 'updated'}.",
            mahajan_id=mahajan_id,
        )
        return normalized

    def delete_mahajan(self, mahajan_id: str) -> bool:
        self.ensure_files()
        mahajan_key = str(mahajan_id or "").strip().upper()
        if not mahajan_key:
            raise ValueError("Mahajan ID is required.")
        existing = self.get_mahajan(mahajan_key)
        if not existing:
            raise ValueError("Mahajan not found.")
        linked_materials = [item for item in self.list_raw_materials() if item.get("mahajan_id") == mahajan_key]
        if linked_materials:
            raise ValueError("Delete blocked: remove or reassign linked raw materials first.")
        live_orders = [
            item
            for item in self.list_supply_orders()
            if item.get("mahajan_id") == mahajan_key and item.get("status") not in {"CANCELLED", "CLOSED"}
        ]
        if live_orders:
            raise ValueError("Delete blocked: active mandi supply orders are still linked to this mahajan.")
        return self._archive_record(
            path=self.mahajans_path,
            list_key="mahajans",
            matcher=lambda item: item.get("mahajan_id") == mahajan_key,
            entity_type="mahajan",
            entity_id=mahajan_key,
        )

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
            "description": str(item.get("description") or (existing or {}).get("description") or "").strip(),
            "image_url": str(item.get("image_url") or (existing or {}).get("image_url") or "").strip(),
            "image_file_ref": str(item.get("image_file_ref") or (existing or {}).get("image_file_ref") or "").strip(),
            "thumbnail_url": str(item.get("thumbnail_url") or (existing or {}).get("thumbnail_url") or "").strip(),
            "image_alt_text": str(item.get("image_alt_text") or (existing or {}).get("image_alt_text") or "").strip(),
            "image_status": str(item.get("image_status") or (existing or {}).get("image_status") or "NONE").strip().upper(),
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
        self._audit("UPSERT_RAW_MATERIAL", "raw_material", material_id, {"status": normalized.get("status", ""), "mahajan_id": normalized.get("mahajan_id", "")})
        self._emit_event(
            "RAW_MATERIAL_UPDATED" if existing else "RAW_MATERIAL_CREATED",
            entity_type="RAW_MATERIAL",
            entity_id=material_id,
            title="Raw material saved",
            message=f"Raw material {normalized.get('name', material_id)} was {'updated' if existing else 'created'}.",
            mahajan_id=normalized.get("mahajan_id", ""),
        )
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
        self._audit("UPSERT_SUPPLY_ORDER", "supply_order", order_id, {"status": normalized.get("status", ""), "mahajan_id": normalized.get("mahajan_id", ""), "manufacturer_id": normalized.get("manufacturer_id", "")})
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
        self._audit("CREATE_SUPPLY_LEDGER_ENTRY", "supply_ledger", str(entry.get("entry_id", "")), {"mandi_order_id": entry.get("mandi_order_id", ""), "status": entry.get("status", "")})
        return entry

    def list_packaging_services(self) -> list[dict[str, Any]]:
        self.ensure_files()
        return self.json_service.read_json(self.packaging_services_path, {"services": []}).get("services", [])

    def get_packaging_service(self, packaging_service_id: str) -> dict[str, Any] | None:
        self.ensure_files()
        key = str(packaging_service_id or "").strip().upper()
        return next((item for item in self.list_packaging_services() if item.get("packaging_service_id") == key), None)

    def upsert_packaging_service(self, service: dict[str, Any]) -> dict[str, Any]:
        self.ensure_files()
        payload = self.json_service.read_json(self.packaging_services_path, {"services": []})
        service_id = str(service.get("packaging_service_id") or "").strip().upper()
        if not service_id:
            raise ValueError("Packaging service ID is required.")
        now = datetime.now(UTC).isoformat()
        existing = next((row for row in payload.get("services", []) if row.get("packaging_service_id") == service_id), None)
        normalized = {
            "packaging_service_id": service_id,
            "name": str(service.get("name") or (existing or {}).get("name") or "").strip(),
            "material_type": str(service.get("material_type") or (existing or {}).get("material_type") or "BOX").strip().upper(),
            "unit": str(service.get("unit") or (existing or {}).get("unit") or "piece").strip(),
            "base_price": round(float(service.get("base_price") if service.get("base_price") is not None else (existing or {}).get("base_price", 0) or 0), 2),
            "price_per_unit": round(float(service.get("price_per_unit") if service.get("price_per_unit") is not None else (existing or {}).get("price_per_unit", 0) or 0), 2),
            "minimum_charge": round(float(service.get("minimum_charge") if service.get("minimum_charge") is not None else (existing or {}).get("minimum_charge", 0) or 0), 2),
            "applicable_product_categories": list(service.get("applicable_product_categories") or (existing or {}).get("applicable_product_categories") or []),
            "status": str(service.get("status") or (existing or {}).get("status") or "ACTIVE").strip().upper(),
            "created_at": (existing or {}).get("created_at") or now,
            "updated_at": now,
        }
        if existing:
            existing.update(normalized)
        else:
            payload.setdefault("services", []).append(normalized)
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.packaging_services_path, payload)
        self._audit("UPSERT_PACKAGING_SERVICE", "packaging_service", service_id, {"status": normalized.get("status", "")})
        return normalized

    def archive_packaging_service(self, packaging_service_id: str) -> bool:
        return self._archive_record(
            path=self.packaging_services_path,
            list_key="services",
            matcher=lambda item: item.get("packaging_service_id") == str(packaging_service_id or "").strip().upper(),
            entity_type="packaging_service",
            entity_id=str(packaging_service_id or "").strip().upper(),
        )

    def list_courier_services(self) -> list[dict[str, Any]]:
        self.ensure_files()
        return self.json_service.read_json(self.courier_services_path, {"services": []}).get("services", [])

    def get_courier_service(self, courier_service_id: str) -> dict[str, Any] | None:
        self.ensure_files()
        key = str(courier_service_id or "").strip().upper()
        return next((item for item in self.list_courier_services() if item.get("courier_service_id") == key), None)

    def upsert_courier_service(self, service: dict[str, Any]) -> dict[str, Any]:
        self.ensure_files()
        payload = self.json_service.read_json(self.courier_services_path, {"services": []})
        service_id = str(service.get("courier_service_id") or "").strip().upper()
        if not service_id:
            raise ValueError("Courier service ID is required.")
        now = datetime.now(UTC).isoformat()
        existing = next((row for row in payload.get("services", []) if row.get("courier_service_id") == service_id), None)
        normalized = {
            "courier_service_id": service_id,
            "provider_name": str(service.get("provider_name") or (existing or {}).get("provider_name") or "").strip(),
            "service_type": str(service.get("service_type") or (existing or {}).get("service_type") or "LOCAL").strip().upper(),
            "base_price": round(float(service.get("base_price") if service.get("base_price") is not None else (existing or {}).get("base_price", 0) or 0), 2),
            "price_per_km": round(float(service.get("price_per_km") if service.get("price_per_km") is not None else (existing or {}).get("price_per_km", 0) or 0), 2),
            "price_per_kg": round(float(service.get("price_per_kg") if service.get("price_per_kg") is not None else (existing or {}).get("price_per_kg", 0) or 0), 2),
            "minimum_charge": round(float(service.get("minimum_charge") if service.get("minimum_charge") is not None else (existing or {}).get("minimum_charge", 0) or 0), 2),
            "supported_locations": list(service.get("supported_locations") or (existing or {}).get("supported_locations") or []),
            "contact_name": str(service.get("contact_name") or (existing or {}).get("contact_name") or "").strip(),
            "contact_mobile": str(service.get("contact_mobile") or (existing or {}).get("contact_mobile") or "").strip(),
            "status": str(service.get("status") or (existing or {}).get("status") or "ACTIVE").strip().upper(),
            "created_at": (existing or {}).get("created_at") or now,
            "updated_at": now,
        }
        if existing:
            existing.update(normalized)
        else:
            payload.setdefault("services", []).append(normalized)
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.courier_services_path, payload)
        self._audit("UPSERT_COURIER_SERVICE", "courier_service", service_id, {"status": normalized.get("status", "")})
        return normalized

    def archive_courier_service(self, courier_service_id: str) -> bool:
        return self._archive_record(
            path=self.courier_services_path,
            list_key="services",
            matcher=lambda item: item.get("courier_service_id") == str(courier_service_id or "").strip().upper(),
            entity_type="courier_service",
            entity_id=str(courier_service_id or "").strip().upper(),
        )

    def list_mandiplace_orders(self) -> list[dict[str, Any]]:
        self.ensure_files()
        return self.json_service.read_json(self.mandiplace_orders_path, {"orders": []}).get("orders", [])

    def get_mandiplace_order(self, mandiplace_order_id: str) -> dict[str, Any] | None:
        self.ensure_files()
        key = str(mandiplace_order_id or "").strip().upper()
        return next((item for item in self.list_mandiplace_orders() if item.get("mandiplace_order_id") == key), None)

    def upsert_mandiplace_order(self, order: dict[str, Any]) -> dict[str, Any]:
        self.ensure_files()
        payload = self.json_service.read_json(self.mandiplace_orders_path, {"orders": []})
        order_id = str(order.get("mandiplace_order_id") or "").strip().upper()
        if not order_id:
            raise ValueError("MandiPlace order ID is required.")
        now = datetime.now(UTC).isoformat()
        existing = next((row for row in payload.get("orders", []) if row.get("mandiplace_order_id") == order_id), None)
        normalized = dict(existing or {})
        normalized.update(order)
        normalized["mandiplace_order_id"] = order_id
        normalized["updated_at"] = now
        normalized["created_at"] = normalized.get("created_at") or now
        if existing:
            existing.update(normalized)
        else:
            payload.setdefault("orders", []).append(normalized)
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.mandiplace_orders_path, payload)
        self._audit(
            "UPSERT_MANDIPLACE_ORDER",
            "mandiplace_order",
            order_id,
            {
                "status": normalized.get("status", ""),
                "requesting_manufacturer_id": normalized.get("requesting_manufacturer_id", ""),
                "supplier_manufacturer_id": normalized.get("supplier_manufacturer_id", ""),
            },
        )
        return normalized

    def _archive_record(
        self,
        *,
        path: Path,
        list_key: str,
        matcher,
        entity_type: str,
        entity_id: str,
        extra_updates: dict[str, Any] | None = None,
    ) -> bool:
        self.ensure_files()
        payload = self.json_service.read_json(path, {list_key: []})
        updated = False
        for item in payload.get(list_key, []):
            if matcher(item):
                item["status"] = "ARCHIVED"
                item["updated_at"] = datetime.now(UTC).isoformat()
                for key, value in (extra_updates or {}).items():
                    item[key] = value
                updated = True
                break
        if not updated:
            return False
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(path, payload)
        self._audit(f"ARCHIVE_{entity_type.upper()}", entity_type, entity_id, {"status": "ARCHIVED"})
        self._emit_event(
            "ARCHIVED",
            entity_type=entity_type.upper(),
            entity_id=entity_id,
            title=f"{entity_type.title()} archived",
            message=f"{entity_type.title()} {entity_id} was archived.",
        )
        return True

    def _audit(self, action: str, entity_type: str, entity_id: str, details: dict[str, Any]) -> None:
        if not self.audit_service:
            return
        self.audit_service.log_governance_event(
            actor="system",
            role="system",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )

    def _emit_event(self, event_type: str, **payload: Any) -> None:
        if not self.event_notification_service:
            return
        self.event_notification_service.emit(event_type, payload)
