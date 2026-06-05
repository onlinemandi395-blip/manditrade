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
    def procurement_sources_path(self) -> Path:
        return self.governance_root / "procurement_sources.json"

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

    @property
    def warehouses_path(self) -> Path:
        return self.governance_root / "warehouses.json"

    @property
    def shipments_path(self) -> Path:
        return self.governance_root / "shipments.json"

    @property
    def financial_transactions_path(self) -> Path:
        return self.governance_root / "financial_transactions.json"

    @property
    def disputes_path(self) -> Path:
        return self.governance_root / "disputes.json"

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
        if not self.procurement_sources_path.exists():
            self.safe_drive_write_service.replace_document(
                self.procurement_sources_path,
                {"schema_version": "1.0", "procurement_sources": []},
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
        if not self.warehouses_path.exists():
            self.safe_drive_write_service.replace_document(
                self.warehouses_path,
                {"schema_version": "1.0", "warehouses": []},
            )
        if not self.shipments_path.exists():
            self.safe_drive_write_service.replace_document(
                self.shipments_path,
                {"schema_version": "1.0", "shipments": []},
            )
        if not self.financial_transactions_path.exists():
            self.safe_drive_write_service.replace_document(
                self.financial_transactions_path,
                {"schema_version": "1.0", "transactions": []},
            )
        if not self.disputes_path.exists():
            self.safe_drive_write_service.replace_document(
                self.disputes_path,
                {"schema_version": "1.0", "disputes": []},
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

    def list_procurement_sources(
        self,
        *,
        include_legacy: bool = True,
        active_only: bool = False,
        source_type: str | None = None,
        product_id: str | None = None,
    ) -> list[dict[str, Any]]:
        self.ensure_files()
        rows = self.json_service.read_json(self.procurement_sources_path, {"procurement_sources": []}).get("procurement_sources", [])
        normalized_rows = [self._normalize_procurement_source_shape(item) for item in rows]
        if include_legacy:
            merged: dict[str, dict[str, Any]] = {item.get("source_id", ""): item for item in normalized_rows if item.get("source_id")}
            for item in self._legacy_manufacturers_as_sources():
                merged.setdefault(item["source_id"], item)
            for item in self._legacy_mahajans_as_sources():
                merged.setdefault(item["source_id"], item)
            normalized_rows = list(merged.values())
        if active_only:
            normalized_rows = [item for item in normalized_rows if str(item.get("status", "")).upper() == "ACTIVE"]
        if source_type:
            source_type_key = str(source_type).strip().upper()
            normalized_rows = [item for item in normalized_rows if str(item.get("source_type", "")).upper() == source_type_key]
        if product_id:
            product_key = str(product_id).strip().upper()
            normalized_rows = [
                item
                for item in normalized_rows
                if product_key in {str(value).strip().upper() for value in item.get("products_supported", []) or []}
            ]
        return sorted(
            normalized_rows,
            key=lambda item: (
                0 if str(item.get("status", "")).upper() == "ACTIVE" else 1,
                str(item.get("business_name", "")).strip().lower(),
                str(item.get("source_id", "")).strip().lower(),
            ),
        )

    def generate_next_procurement_source_id(self) -> str:
        self.ensure_files()
        highest_suffix = 0
        for item in self.list_procurement_sources(include_legacy=False):
            source_id = str(item.get("source_id") or "").strip().upper()
            match = re.fullmatch(r"SRC(\d+)", source_id)
            if match:
                highest_suffix = max(highest_suffix, int(match.group(1)))
        return f"SRC{highest_suffix + 1:03d}"

    def get_procurement_source(self, source_id: str) -> dict[str, Any] | None:
        self.ensure_files()
        source_key = str(source_id or "").strip().upper()
        return next((item for item in self.list_procurement_sources(include_legacy=True) if item.get("source_id") == source_key), None)

    def upsert_procurement_source(self, source: dict[str, Any]) -> dict[str, Any]:
        self.ensure_files()
        payload = self.json_service.read_json(self.procurement_sources_path, {"procurement_sources": []})
        source_id = str(source.get("source_id") or "").strip().upper()
        if not source_id:
            raise ValueError("Procurement source ID is required.")
        now = datetime.now(UTC).isoformat()
        existing = next((item for item in payload.get("procurement_sources", []) if str(item.get("source_id", "")).strip().upper() == source_id), None)
        normalized = self._normalize_procurement_source_shape({**(existing or {}), **source, "source_id": source_id})
        normalized["created_at"] = (existing or {}).get("created_at") or normalized.get("created_at") or now
        normalized["updated_at"] = now
        if existing:
            existing.update(normalized)
        else:
            payload.setdefault("procurement_sources", []).append(normalized)
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.procurement_sources_path, payload)
        self._audit(
            "UPSERT_PROCUREMENT_SOURCE",
            "procurement_source",
            source_id,
            {"status": normalized.get("status", ""), "source_type": normalized.get("source_type", "")},
        )
        return normalized

    def archive_procurement_source(self, source_id: str) -> bool:
        source_key = str(source_id or "").strip().upper()
        if source_key.startswith("MANU-") or source_key.startswith("MAHAJAN-"):
            raise ValueError("Legacy manufacturer/mahajan source aliases cannot be archived from Procurement Sources.")
        return self._archive_record(
            path=self.procurement_sources_path,
            list_key="procurement_sources",
            matcher=lambda item: str(item.get("source_id", "")).strip().upper() == source_key,
            entity_type="procurement_source",
            entity_id=source_key,
        )

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
        categories = mahajan.get("raw_material_categories", (existing or {}).get("raw_material_categories", [])) or []
        states_served = mahajan.get("states_served", (existing or {}).get("states_served", [])) or []
        if isinstance(categories, str):
            categories = [item.strip() for item in categories.split(",") if item.strip()]
        else:
            categories = [str(item).strip() for item in categories if str(item).strip()]
        if isinstance(states_served, str):
            states_served = [item.strip() for item in states_served.split(",") if item.strip()]
        else:
            states_served = [str(item).strip() for item in states_served if str(item).strip()]
        existing_address = (existing or {}).get("address", {}) or {}
        address = mahajan.get("address", {}) or {}
        banking = mahajan.get("banking", {}) or {}
        existing_banking = (existing or {}).get("banking", {}) or {}
        normalized = {
            "mahajan_id": mahajan_id,
            "business_name": str(mahajan.get("business_name") or (existing or {}).get("business_name") or "").strip(),
            "owner_name": str(mahajan.get("owner_name") or (existing or {}).get("owner_name") or "").strip(),
            "email": email,
            "mobile": str(mahajan.get("mobile") or (existing or {}).get("mobile") or "").strip(),
            "city": str(mahajan.get("city") or (existing or {}).get("city") or "").strip(),
            "coverage_area": str(mahajan.get("coverage_area") or (existing or {}).get("coverage_area") or "").strip(),
            "states_served": states_served,
            "raw_material_categories": categories,
            "minimum_order_qty": float(mahajan.get("minimum_order_qty") or (existing or {}).get("minimum_order_qty") or 0),
            "rating": float(mahajan.get("rating") or (existing or {}).get("rating") or 0),
            "status": str(mahajan.get("status") or (existing or {}).get("status") or "PENDING").strip().upper(),
            "address": {
                "line1": str(address.get("line1") or existing_address.get("line1") or "").strip(),
                "line2": str(address.get("line2") or existing_address.get("line2") or "").strip(),
                "city": str(address.get("city") or mahajan.get("city") or existing_address.get("city") or (existing or {}).get("city") or "").strip(),
                "state": str(address.get("state") or existing_address.get("state") or "").strip(),
                "pin_code": str(address.get("pin_code") or existing_address.get("pin_code") or "").strip(),
            },
            "banking": {
                "account_holder_name": str(banking.get("account_holder_name") or existing_banking.get("account_holder_name") or "").strip(),
                "account_number": str(banking.get("account_number") or existing_banking.get("account_number") or "").strip(),
                "ifsc": str(banking.get("ifsc") or existing_banking.get("ifsc") or "").strip().upper(),
                "upi_id": str(banking.get("upi_id") or existing_banking.get("upi_id") or "").strip(),
            },
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
            "tax_profile": dict(item.get("tax_profile") or (existing or {}).get("tax_profile") or {}),
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
            "tax_profile": dict(service.get("tax_profile") or (existing or {}).get("tax_profile") or {}),
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
            "tax_profile": dict(service.get("tax_profile") or (existing or {}).get("tax_profile") or {}),
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

    def list_warehouses(self, *, owner_role: str | None = None, owner_id: str | None = None) -> list[dict[str, Any]]:
        self.ensure_files()
        rows = self.json_service.read_json(self.warehouses_path, {"warehouses": []}).get("warehouses", [])
        if owner_role:
            rows = [item for item in rows if str(item.get("owner_role", "")).strip().lower() == str(owner_role).strip().lower()]
        if owner_id:
            rows = [item for item in rows if str(item.get("owner_id", "")).strip().upper() == str(owner_id).strip().upper()]
        return rows

    def get_warehouse(self, warehouse_id: str) -> dict[str, Any] | None:
        self.ensure_files()
        key = str(warehouse_id or "").strip().upper()
        return next((item for item in self.list_warehouses() if item.get("warehouse_id") == key), None)

    def upsert_warehouse(self, warehouse: dict[str, Any]) -> dict[str, Any]:
        self.ensure_files()
        payload = self.json_service.read_json(self.warehouses_path, {"warehouses": []})
        warehouse_id = str(warehouse.get("warehouse_id") or "").strip().upper()
        if not warehouse_id:
            raise ValueError("Warehouse ID is required.")
        now = datetime.now(UTC).isoformat()
        existing = next((row for row in payload.get("warehouses", []) if row.get("warehouse_id") == warehouse_id), None)
        normalized = {
            "warehouse_id": warehouse_id,
            "owner_role": str(warehouse.get("owner_role") or (existing or {}).get("owner_role") or "").strip().lower(),
            "owner_id": str(warehouse.get("owner_id") or (existing or {}).get("owner_id") or "").strip().upper(),
            "warehouse_name": str(warehouse.get("warehouse_name") or (existing or {}).get("warehouse_name") or "").strip(),
            "contact_person": str(warehouse.get("contact_person") or (existing or {}).get("contact_person") or "").strip(),
            "phone": str(warehouse.get("phone") or (existing or {}).get("phone") or "").strip(),
            "address": str(warehouse.get("address") or (existing or {}).get("address") or "").strip(),
            "city": str(warehouse.get("city") or (existing or {}).get("city") or "").strip(),
            "state": str(warehouse.get("state") or (existing or {}).get("state") or "").strip(),
            "pincode": str(warehouse.get("pincode") or (existing or {}).get("pincode") or "").strip(),
            "latitude": str(warehouse.get("latitude") or (existing or {}).get("latitude") or "").strip(),
            "longitude": str(warehouse.get("longitude") or (existing or {}).get("longitude") or "").strip(),
            "capacity": float(warehouse.get("capacity") if warehouse.get("capacity") is not None else (existing or {}).get("capacity", 0) or 0),
            "status": str(warehouse.get("status") or (existing or {}).get("status") or "ACTIVE").strip().upper(),
            "is_default": bool(warehouse.get("is_default") if warehouse.get("is_default") is not None else (existing or {}).get("is_default", False)),
            "created_at": (existing or {}).get("created_at") or now,
            "updated_at": now,
        }
        if existing:
            existing.update(normalized)
        else:
            payload.setdefault("warehouses", []).append(normalized)
        if normalized["is_default"]:
            for row in payload.get("warehouses", []):
                if row.get("warehouse_id") != warehouse_id and row.get("owner_role") == normalized["owner_role"] and row.get("owner_id") == normalized["owner_id"]:
                    row["is_default"] = False
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.warehouses_path, payload)
        self._audit("UPSERT_WAREHOUSE", "warehouse", warehouse_id, {"owner_role": normalized.get("owner_role", ""), "owner_id": normalized.get("owner_id", ""), "status": normalized.get("status", "")})
        return normalized

    def ensure_default_warehouse(
        self,
        *,
        owner_role: str,
        owner_id: str,
        warehouse_name: str = "",
        city: str = "",
        state: str = "",
        contact_person: str = "",
    ) -> dict[str, Any]:
        existing = next((item for item in self.list_warehouses(owner_role=owner_role, owner_id=owner_id) if item.get("is_default")), None)
        if existing:
            return existing
        owner_key = str(owner_id or "").strip().upper().replace(" ", "")[:6] or str(owner_role or "").strip().upper()[:3]
        warehouse_id = f"{owner_key}-WH{len(self.list_warehouses(owner_role=owner_role, owner_id=owner_id)) + 1:03d}"
        return self.upsert_warehouse(
            {
                "warehouse_id": warehouse_id,
                "owner_role": owner_role,
                "owner_id": owner_id,
                "warehouse_name": warehouse_name or f"{str(owner_id).strip().upper()} Main Warehouse",
                "contact_person": contact_person,
                "city": city,
                "state": state,
                "status": "ACTIVE",
                "is_default": True,
            }
        )

    def list_shipments(self) -> list[dict[str, Any]]:
        self.ensure_files()
        return self.json_service.read_json(self.shipments_path, {"shipments": []}).get("shipments", [])

    def get_shipment(self, shipment_id: str) -> dict[str, Any] | None:
        self.ensure_files()
        key = str(shipment_id or "").strip().upper()
        return next((item for item in self.list_shipments() if item.get("shipment_id") == key), None)

    def upsert_shipment(self, shipment: dict[str, Any]) -> dict[str, Any]:
        self.ensure_files()
        payload = self.json_service.read_json(self.shipments_path, {"shipments": []})
        shipment_id = str(shipment.get("shipment_id") or "").strip().upper()
        if not shipment_id:
            raise ValueError("Shipment ID is required.")
        now = datetime.now(UTC).isoformat()
        existing = next((row for row in payload.get("shipments", []) if row.get("shipment_id") == shipment_id), None)
        normalized = dict(existing or {})
        normalized.update(shipment)
        normalized["shipment_id"] = shipment_id
        normalized["shipment_type"] = str(normalized.get("shipment_type") or "MANDIPLACE").strip().upper()
        normalized["status"] = str(normalized.get("status") or "CREATED").strip().upper()
        normalized["source_warehouse_id"] = str(normalized.get("source_warehouse_id") or "").strip().upper()
        normalized["courier_id"] = str(normalized.get("courier_id") or "").strip().upper()
        normalized["packaging_id"] = str(normalized.get("packaging_id") or "").strip().upper()
        normalized["created_at"] = normalized.get("created_at") or now
        normalized["updated_at"] = now
        if existing:
            existing.update(normalized)
        else:
            payload.setdefault("shipments", []).append(normalized)
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.shipments_path, payload)
        self._audit("UPSERT_SHIPMENT", "shipment", shipment_id, {"status": normalized.get("status", ""), "order_id": normalized.get("order_id", ""), "shipment_type": normalized.get("shipment_type", "")})
        return normalized

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

    def list_financial_transactions(self) -> list[dict[str, Any]]:
        self.ensure_files()
        return self.json_service.read_json(self.financial_transactions_path, {"transactions": []}).get("transactions", [])

    def get_financial_transaction(self, financial_transaction_id: str) -> dict[str, Any] | None:
        self.ensure_files()
        key = str(financial_transaction_id or "").strip().upper()
        return next((item for item in self.list_financial_transactions() if item.get("financial_transaction_id") == key), None)

    def upsert_financial_transaction(self, transaction: dict[str, Any]) -> dict[str, Any]:
        self.ensure_files()
        payload = self.json_service.read_json(self.financial_transactions_path, {"transactions": []})
        transaction_id = str(transaction.get("financial_transaction_id") or "").strip().upper()
        if not transaction_id:
            raise ValueError("Financial transaction ID is required.")
        now = datetime.now(UTC).isoformat()
        existing = next((row for row in payload.get("transactions", []) if row.get("financial_transaction_id") == transaction_id), None)
        normalized = dict(existing or {})
        normalized.update(transaction)
        normalized["financial_transaction_id"] = transaction_id
        normalized["updated_at"] = now
        normalized["created_at"] = normalized.get("created_at") or now
        normalized["version"] = int(normalized.get("version", 1) or 1)
        if existing:
            existing.update(normalized)
        else:
            payload.setdefault("transactions", []).append(normalized)
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.financial_transactions_path, payload)
        self._audit(
            "UPSERT_FINANCIAL_TRANSACTION",
            "financial_transaction",
            transaction_id,
            {
                "status": normalized.get("status", ""),
                "transaction_type": normalized.get("transaction_type", ""),
                "related_order_id": normalized.get("related_order_id", ""),
            },
        )
        return normalized

    def list_disputes(self) -> list[dict[str, Any]]:
        self.ensure_files()
        return self.json_service.read_json(self.disputes_path, {"disputes": []}).get("disputes", [])

    def get_dispute(self, dispute_id: str) -> dict[str, Any] | None:
        self.ensure_files()
        key = str(dispute_id or "").strip().upper()
        return next((item for item in self.list_disputes() if item.get("dispute_id") == key), None)

    def upsert_dispute(self, dispute: dict[str, Any]) -> dict[str, Any]:
        self.ensure_files()
        payload = self.json_service.read_json(self.disputes_path, {"disputes": []})
        dispute_id = str(dispute.get("dispute_id") or "").strip().upper()
        if not dispute_id:
            raise ValueError("Dispute ID is required.")
        now = datetime.now(UTC).isoformat()
        existing = next((row for row in payload.get("disputes", []) if row.get("dispute_id") == dispute_id), None)
        normalized = dict(existing or {})
        normalized.update(dispute)
        normalized["dispute_id"] = dispute_id
        normalized["updated_at"] = now
        normalized["created_at"] = normalized.get("created_at") or now
        normalized["version"] = int(normalized.get("version", 1) or 1)
        if existing:
            existing.update(normalized)
        else:
            payload.setdefault("disputes", []).append(normalized)
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.disputes_path, payload)
        self._audit(
            "UPSERT_DISPUTE",
            "dispute",
            dispute_id,
            {
                "status": normalized.get("status", ""),
                "related_transaction_id": normalized.get("related_transaction_id", ""),
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

    def _normalize_procurement_source_shape(self, source: dict[str, Any]) -> dict[str, Any]:
        normalized_source_id = str(source.get("source_id") or "").strip().upper()
        supported_products = source.get("products_supported", []) or source.get("source_ids", []) or []
        if isinstance(supported_products, str):
            supported_products = [item.strip().upper() for item in supported_products.split(",") if item.strip()]
        else:
            supported_products = [str(item).strip().upper() for item in supported_products if str(item).strip()]
        return {
            "source_id": normalized_source_id,
            "source_type": str(source.get("source_type") or "EXTERNAL").strip().upper(),
            "business_name": str(source.get("business_name") or source.get("name") or "").strip(),
            "contact_person": str(source.get("contact_person") or source.get("owner_name") or source.get("contact_name") or "").strip(),
            "mobile": str(source.get("mobile") or source.get("phone") or source.get("contact_mobile") or "").strip(),
            "email": str(source.get("email") or source.get("owner_email") or "").strip().lower(),
            "city": str(source.get("city") or "").strip(),
            "state": str(source.get("state") or ((source.get("address") or {}).get("state")) or "").strip(),
            "products_supported": supported_products,
            "status": str(source.get("status") or "ACTIVE").strip().upper(),
            "legacy_entity_type": str(source.get("legacy_entity_type") or "").strip().upper(),
            "legacy_entity_id": str(source.get("legacy_entity_id") or "").strip().upper(),
            "notes": str(source.get("notes") or "").strip(),
            "created_at": str(source.get("created_at") or "").strip(),
            "updated_at": str(source.get("updated_at") or "").strip(),
        }

    def _legacy_manufacturers_as_sources(self) -> list[dict[str, Any]]:
        sources: list[dict[str, Any]] = []
        for item in self.list_manufacturers():
            manufacturer_code = str(item.get("manufacturer_code") or "").strip().upper()
            if not manufacturer_code:
                continue
            normalized = self._normalize_procurement_source_shape(
                {
                    "source_id": f"MANU-{manufacturer_code}",
                    "source_type": "MANUFACTURER",
                    "business_name": item.get("business_name") or item.get("manufacturer_name") or manufacturer_code,
                    "contact_person": item.get("contact_person") or item.get("owner_name") or "",
                    "mobile": item.get("mobile") or "",
                    "email": item.get("owner_email") or "",
                    "city": item.get("city") or ((item.get("address") or {}).get("city")) or "",
                    "state": ((item.get("address") or {}).get("state")) or "",
                    "products_supported": item.get("product_categories") or [],
                    "status": item.get("status") or "PENDING",
                    "legacy_entity_type": "MANUFACTURER",
                    "legacy_entity_id": manufacturer_code,
                    "notes": "Legacy manufacturer identity exposed as a procurement source for compatibility.",
                    "created_at": item.get("created_at") or "",
                    "updated_at": item.get("updated_at") or "",
                }
            )
            sources.append(normalized)
        return sources

    def _legacy_mahajans_as_sources(self) -> list[dict[str, Any]]:
        sources: list[dict[str, Any]] = []
        for item in self.list_mahajans():
            mahajan_id = str(item.get("mahajan_id") or "").strip().upper()
            if not mahajan_id:
                continue
            normalized = self._normalize_procurement_source_shape(
                {
                    "source_id": f"MAHAJAN-{mahajan_id}",
                    "source_type": "MAHAJAN",
                    "business_name": item.get("business_name") or mahajan_id,
                    "contact_person": item.get("owner_name") or "",
                    "mobile": item.get("mobile") or "",
                    "email": item.get("email") or "",
                    "city": item.get("city") or ((item.get("address") or {}).get("city")) or "",
                    "state": ((item.get("address") or {}).get("state")) or "",
                    "products_supported": item.get("raw_material_categories") or [],
                    "status": item.get("status") or "PENDING",
                    "legacy_entity_type": "MAHAJAN",
                    "legacy_entity_id": mahajan_id,
                    "notes": "Legacy mahajan identity exposed as a procurement source for compatibility.",
                    "created_at": item.get("created_at") or "",
                    "updated_at": item.get("updated_at") or "",
                }
            )
            sources.append(normalized)
        return sources

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
